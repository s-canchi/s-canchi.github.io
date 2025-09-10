---
layout: post
title: Slurm Arrays for Omics Data
subtitle: Scaling up with arrays, chunks, and job handling 
tags: [Slurm, bash, HPC]
comments: true
---

When analyzing dozens or thousands of omics datasets, it is essential to parallelize the compute. In this post, I showcase a couple of ways for large-scale batch analysis on high-performance computing (HPC).

## What is Slurm ? 

Slurm (Simple Linux Utility for Resource Management) is an open-source workload manager and job scheduler used by many research computing clusters. A good analogy here would be a large, bustling restaurant kitchen. Dozens of chefs (researchers) hand in orders (jobs), each needing different ingredients and cook times. Slurm acts as the head chef and kitchen manager. It reads every order, checks what equipment and ingredients are needed, and decides not just who cooks what, but when and in which part of the kitchen. This careful orchestration ensures efficient use of space and staff, prevents bottlenecks at the stoves, and helps every dish arrive on time.

For situations where many near-identical orders come in (like a banquet with hundreds of similar plates), Slurm can use job arrays to batch, track, and distribute the work so each plate (job) is prepared efficiently and in parallel, without mixing up the recipes (workflows).

In short, Slurm is the coordinator behind the scenes, ensuring smooth and efficient delivery of each computational dish on a shared cluster.

{: .box-note}
**Resource:** Official Slurm [documentation](https://slurm.schedmd.com/documentation.html) lists many useful commands. 

## Slurm Arrays: simple way to batch 

A Slurm array is an efficient way to run the same command or workflow across many samples or datasets with a single job submission. 

An array is a collection of data items; like a list in Python `(["sampleA", "sampleB", "sampleC"])` or a vector in R `(c("sampleA", "sampleB", "sampleC"))`. When you use a `for` or `while` loop in R or Python, you are instructing the computer to perform the same operation repeatedly on each element in the list. 

The same looping logic is translated to the cluster when you use a Slurm Array. Essentially Slurm executes the task in parallel for all the samples in the array. Each job in the array receives a unique task index (`Slurm_ARRAY_TASK_ID`) which allows the script to determine which sample or dataset to work on during that particular run. This allows for efficient and automatic processing of many samples at once, without having to submit each job individually.

```
Manual for-loop jobs:
  sbatch job_for_sampleA
  sbatch job_for_sampleB
  sbatch job_for_sampleC
      |
      +--> Scheduler runs each job as an independent submission

Slurm array job:
  sbatch --array=1-3 run_pipeline.sh
      |
      +--> Scheduler runs: job.1    job.2    job.3
                              |        |        |
                          [sampleA][sampleB][sampleC]

   (each job gets a unique Slurm_ARRAY_TASK_ID)
```    

### Example script

The file `sample_ids.txt` should contain the list of your sample names (or datasets) , one per line, and will be used to map each array job to a specific sample. For example:

```
sampleA
sampleB
sampleC
...
```

```bash
#!/bin/bash
#SBATCH --job-name=sample_array_job
#SBATCH --output=slurm_logs/%A_%a.out
#SBATCH --error=slurm_logs/%A_%a.err
#SBATCH --time=HH:MM:SS
#SBATCH --mem=XXG
#SBATCH --cpus-per-task=N
#SBATCH --partition=<name of partition as defined in the HPC>
#SBATCH --mail-type=END,FAIL,ARRAY_TASKS
#SBATCH --account=my_account

# Set paths
base_dir="/path/to/data"
sample_list="${base_dir}/sample_ids.txt"

# Get the sample for this array task (1-based index)
sample=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${sample_list}")

echo "Processing sample ${sample} (Array Task ID: ${SLURM_ARRAY_TASK_ID})"

# Make sample-specific output directory 
output_dir="${base_dir}/outputs/${sample}"
mkdir -p "${output_dir}"

# Activate env
source /path/to/conda.sh
conda activate my_env

# Run the analysis
Rscript my_analysis_script.R "${sample}" > "${output_dir}/${sample}_out.txt" 2>&1

# Deactivate env
conda deactivate
```

The Slurm job directives used here are:

| SBATCH option         | Purpose                                   |
|-----------------------|----------------------------------------------------------|
| `--job-name`          | Name for monitoring in the queue/job list                |
| `--output`            | Output file for standard output (per array/task/job)     |
| `--error`             | Output file for standard error (per array/task/job)      |
| `--time`              | Maximum run time (hh:mm:ss)                              |
| `--mem`               | Memory per task                                          |
| `--cpus-per-task`     | Number of CPU cores for each task                        |
| `--partition`         | Which partition or queue to use (HPC specific)                          |
| `--mail-type`         | When to send email notifications                         |
| `--account`           | Charge jobs to this account/project                      |


To keep the job submission script reusable for any dataset length, we can auto-assign the array length based on sample list.

```bash
$ sbatch --array=1-$(wc -l < /path/to/data/sample_ids.txt) run_array_job.sh
```

## Is there a limit to array size ?

Yes! This is specific to each HPC system configuration. The key parameter to look out for the is `MaxArraySize` which defines the maximum number of tasks in a single job array. This value will be cluster specific and you can use `scontrol` to get actual values. For example, 

```bash
$ scontrol show config | grep MaxArraySize
```
So the `N` in your job submission should always be less than or equal to `MaxArraySize` parameter on each cluster (i.e., `--array=1-N` where `N ≤ MaxArraySize`). 

{: .box-note}
**Tip:** To get a glimpse of your cluster specific variables, you can use `scontrol` to query the config parameters:
`scontrol show config | grep -Ei 'max|limit|partition|user|account|array'`

Even if you don’t see explicit user or group job limits in cluster configuration, real parallelism is always governed by available cluster resources and scheduler policies. Submitting an array task of `MaxArraySize` does not mean all N tasks will run at once. The running jobs will be limited by both the physical resources available and any user/job concurrency policies (which may not be visible in `scontrol show config`).

For best throughput, reach out to your HPC administrators for definitive guidance on practical and policy limits for user job concurrency and resource allocation.

## How to proceed if your sample size exceeds the array size limits ?

If the total number of samples (S) is larger than the allowed `MaxArraySize`, you can employ chunking i.e., split your samples into several smaller lists or chunks and have each array job process one chunk at a time.

```
Full sample_ids.txt:         [sample1, sample2, ... sampleS]
      |
      |
  [split into K-sized chunks]
      |
      +---> chunk_manifest.txt:
                chunk_00.txt    # (samples 1 to K)
                chunk_01.txt    # (samples K+1 to 2K)
                ...
                chunk_N.txt

Run: sbatch --array=1-$(wc -l < chunk_manifest.txt) run_chunked_array.sh

For task i (SLURM_ARRAY_TASK_ID=i):
   Reads: chunk_file = $(sed -n "${SLURM_ARRAY_TASK_ID}p" chunk_manifest.txt)
   Processes every sample in chunk_file (typically K samples)
```  

So now instead of each array mapping to an individual sample, it maps to K samples. You can use the cluster level limits to calculate the chunk size. For example, if

```
S = total number of samples
K = desired chunk size i.e., samples/chunk (should be ≤ MaxArraySize)
N = number of array jobs (chunks)

# Optimal chunk size to allow maximum parallelism 
## Actual parallel jobs running/user = min(user concurrency limit, available resources, partition policies) which is usually less than N.
## Use min of N and user limits to get the optimal chunk size

N = MaxArraySize
K = ceil(S / N)

# Then, split the samples into N chunk files 
(each up to K samples)
```

{: .box-note}
**Note:** Ensure N (`sbatch --array=1-N`) does not exceed `MaxArraySize`. K can be any positive integer; the real constraint is on N, not K.

### Example script

So translating the chunking logic, we first need to generate the `chunk_manifest.txt` file:

```bash
#!/bin/bash

# Set paths
base_dir="/path/to/data"
sample_list="${base_dir}/sample_ids.txt"

# Get total number of samples
S=$(wc -l < "$sample_list")

# Get MaxArraySize from Slurm 
MAX_ARRAY_SIZE=$(scontrol show config 2>/dev/null | awk -F= '/MaxArraySize/ {print $2}' | xargs)
if [[ -z "$MAX_ARRAY_SIZE" || "$MAX_ARRAY_SIZE" = "0" ]]; then
    echo "WARNING: Could not determine MaxArraySize from Slurm config."
    echo "Please check your cluster settings and manually set this value if needed."
    exit 1
fi

N=$MAX_ARRAY_SIZE

# Get optimal chunk size
K=$(( (S + N - 1) / N ))

echo "Splitting $S samples into $N chunks (each with up to $K samples)..."

mkdir -p chunks

# Split the sample list into N chunks
split -d -n l/$N "$sample_list" chunks/chunk_

cd chunks
for f in chunk_*; do
  mv "$f" "$f.txt"
done
cd ..

ls chunks/chunk_*.txt > chunk_manifest.txt

echo "Created $(wc -l < chunk_manifest.txt) chunk files, listed in chunk_manifest.txt"
```

We then update the Slurm job submission script for the chunk logic:

```bash
#!/bin/bash
#SBATCH --job-name=sample_chunk_job
#SBATCH --output=slurm_logs/%A_%a.out
#SBATCH --error=slurm_logs/%A_%a.err
#SBATCH --time=HH:MM:SS
#SBATCH --mem=XXG
#SBATCH --cpus-per-task=N
#SBATCH --partition=<name of partition as defined in the HPC>
#SBATCH --mail-type=END,FAIL,ARRAY_TASKS
#SBATCH --account=my_account

# Set paths
base_dir="/path/to/data"
chunk_manifest="${base_dir}/chunk_manifest.txt"   # created from the chunking script

# Get the chunk file for this array task (1-based index)
chunk_file=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${chunk_manifest}")

echo "Processing chunk file: ${chunk_file} (Array Task ID: ${SLURM_ARRAY_TASK_ID})"

# Activate env
source /path/to/conda.sh
conda activate my_env

# Loop over every sample in this chunk file
while read -r sample; do
    echo "Processing sample: ${sample}"
    output_dir="${base_dir}/outputs/${sample}"
    mkdir -p "${output_dir}"

    # Run analysis, redirect each sample's output
    Rscript my_analysis_script.R "${sample}" > "${output_dir}/${sample}_out.txt" 2>&1
done < "${chunk_file}"

# Deactivate env
conda deactivate
```

Proceed with job submission as before:

```bash 
$ sbatch --array=1-$(wc -l < chunk_manifest.txt) run_chunked_array.sh
```

## Take away

Both per-sample array tasks and chunking have their advantages. Use single-sample tasks for straightforward tracking and flexibility. Switch to chunking when faced with cluster limits or have jobs with short runtimes. There is no one-size-fits-all. Your specific task and your cluster’s policies will almost always determine the best strategy for efficiency and parallelism.

| **Task**                                                        | **Strategy**                 |
|-----------------------------------------------------------------|------------------------------------------|
| Fine-grained job tracking and control needed                    | One array task per sample                |
| Sample count exceeds array size or job limits                   | Chunking: multiple samples per array task|
| Samples have similar resource needs                             | Either approach works                    |
| Jobs with short runtime                       | Chunking to reduce scheduler overhead    |
| Need to re-run or monitor specific samples easily               | One array task per sample                |
| Cluster docs recommend avoiding many small jobs                 | Chunking                                 |

