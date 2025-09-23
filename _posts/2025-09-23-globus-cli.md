---
layout: post
title: Globus CLI for Data Transfers
subtitle: Selective, Scripted, and Shareable Transfers
tags: [Globus, bash, data management, automation]
comments: true
---

Like many researchers, I work across fast *hot* storage (scratch or SSD) and slow, cost-effective *cold* archives. Managing data across these tiers often means moving files between large, tape-backed archival systems and higher-performance disks for active analysis. My institution uses Globus for these transfers, which generally offers a smooth experience, especially through its web interface.

However, I have found certain usecases (e.g., estimating the size of nested folders, selecting just a handful of specific files or directories, or preparing batch transfers based on patterns) are not as straightforward to handle through the user interface. In these situations, I turn to the `globus-cli` which is command line interface for globus and some basic scripting to fill the gaps and make these specialized tasks more efficient and reproducible.

In this post, I will share examples of how I use `globus-cli` for targeted file retrieval, size estimation, and batch script generation when a point and click workflow isn’t enough. If your computing environment provides Globus and you find yourself with similar needs, you might find these patterns useful (or at least adaptable).

# Globus, Endpoints & CLI Overview

**Globus** is a tool for transferring and sharing data between storage systems of all kinds; high-performance compute (HPC) clusters, tape or archival storage, cloud storage, and personal laptops. It manages large dataset transfers, handles failure and resume automatically, and can bridge systems that otherwise would not talk to each other.

**Endpoints** are the defined entry and exit points for data on the Globus network, much like designated docks in a shipping port. These might be large institutional storage servers, a lab’s scratch directory, a tape archive, or even your personal laptop. Endpoints are **fixed entities** i.e., once an endpoint is assigned, its identifier does not change unless the underlying system is reconfigured or decommissioned. This identifier is a Universally Unique Identifier (UUID). Additionally, all defined endpoints are **discoverable** via Globus, and hence, whether you are scripting or searching, you can reliably find and reference them for your transfers.

The `globus-cli` is a command-line tool for exploring, transferring, or scripting batch jobs between endpoints. While the web interface is great for interactive use, the CLI is ideal for automation or more complex workflows.

## Check/install Globus CLI on any HPC

Most HPCs using Globus would most likely make `globus-cli` available as a module. You can check using:

```bash
module spider globus-cli
```

or

```bash
module avail globus-cli
```

If you are not sure of the exact spelling or want to list all related modules, you can use:

```bash
module avail globus
```

If available, you can easily load it for your session:

```bash
module load globus-cli
```

{: .box-note}
**Tip**: Follow the [official install instructions](https://docs.globus.org/cli/) which recommends pip or pipx. You can also use `conda` to install:<br>
`conda install conda-forge::globus-cli`

## Globus in my workflow

A quick overview of some of my most common use cases:

```
Within one HPC cluster:

+-----------------+        +-------------------+
|  Active Storage | <----> | Archive Storage   |
+-----------------+        +-------------------+

Between HPC clusters (also via archives):

+----------------------+         +-----------------------+
|       HPC 1          | <-----> |         HPC 2         |
+----------------------+         +-----------------------+
           ^                                ^
           |                                |
           +----------------+   +-----------+
                            |   |
                 +--------------------+
                 |  Archive Storage   |
                 +--------------------+

Within institution, sharing with outside groups (using collections):

   +------------------------------+
   |   Lab Group A Collection     |
   +------------------------------+
         |         |            |
         |         |            |
       (read)   (read/write)  (read-only)
         |         |            |
         v         v            v
+-----------+ +-----------+ +-----------+
| Lab B     | | Lab C     | | Lab D     |
+-----------+ +-----------+ +-----------+

Between institutions (using collections):

   +----------------------------------------+
   |       Institution 1 Collection         |
   +----------------------------------------+
        |                |                |
      (read)       (read/write)     (read-only)
        |                |                |
        v                v                v
+----------------+ +----------------+ +-----------------+
| Institution 2  | | Institution 3  | | Institution 4   |
|   Collection   | |   Collection   | |   Collection    |
+----------------+ +----------------+ +-----------------+
```

**Globus Collections** are highly versatile, which allow me to grant tailored access levels (read, write, share) to each institution or individual collaborator, all without needing HPC admin privileges. This enables complex, multi-institutional data sharing workflows that I can control directly.

Without Globus, sharing data between institutions is tedious, error-prone, and often restricts transfer size and data integrity.

```
Without Globus (multi-step workaround):

 (You)
+---------------------+
| Institute 1 HPC     |--------------------------+
+---------------------+                          |
     |                                           | 
     |                                           | 
     v                                           v 
+-------------------+           +-----------------------+
| Managed Device    |---------->| Institution 1 Cloud   |
| (Laptop/Desktop)  |           | (Box/Dropbox/S3/etc.) |
+-------------------+           +-----------------------+
                                          |
                                          v
                (Collaborator)  +---------------------+
                                | Managed Device      |
                                | (Laptop/Desktop)    |
                                +---------------------+
                                         |
                                         v
                                +---------------------+
                                | Institute 2 HPC     |
                                +---------------------+

```                                      

# When I Reach for Globus CLI & Scripting

Before diving into the specific scenarios where the `globus-cli` and some simple scripting have made my life easier, I want to highlight a small setup step that has saved me a lot of time. I keep track of all my frequently used Globus endpoints in a single, central file, and use a custom shell function to access any endpoint by name, whether I am scripting or working at the command line.

## My approach to endpoint lookup

Here are general setup steps:

* **Store endpoints in a central file**: I generally create and place this file in my home directory, updating it whenever I start working with a new collection, cluster, or archive resource.

    ```bash
    ~/globus_endpoints.txt
    ```

    Contents (example UUIDs):

    ```bash
    archive    : ab65757f-00f5-4e5b-aa21-133187732a01
    hpc_1      : f1234567-89ab-4cde-bc10-234567890abc
    hpc_2      : c2345678-90ab-4def-a234-bcdef0123456
    ```

*  **Define and export a function to the shell config file**: Add this to your `~/.bashrc` or preferred shell config:

    ```bash
    #get_endpoint function for Globus
    get_endpoint() {
        key="$1"
        grep -E "^${key}[[:space:]]*:" ~/globus_endpoints.txt | awk -F':' '{print $2}' | xargs
    }
    export -f get_endpoint
    ```

* **Reload shell**: Update the shell for the `get_endpoint` to be globally available.

    ```bash
    source ~/.bashrc
    ```

## Usecase 1: Storage planning, size estimation & quota management

Before any large recall or transfer, I check if the data will actually fit in active storage to avoid quota issues. My approach: always archive raw data, keep only what’s needed for current analysis on fast storage, and move the rest out when it’s no longer active. This keeps costs down and workflows efficient; a data management philosophy I rely on for any big research project. 

Here, I illustrate with an example of estimating FASTQ file sizes in archival storage. Assume the folder structure is:

```
/group_name/project_name/data/
├── Sample01/
│   └── FASTQ/
│        ├── sample01_R1.fastq.gz
│        └── sample01_R2.fastq.gz
├── Sample02/
│   └── FASTQ/
│        ├── sample02_R1.fastq.gz
│        └── sample02_R2.fastq.gz
...
```

Script for estimating size:

```bash
#!/bin/bash

module load globus-cli

# Assumes get_endpoint() is exported from your shell config (see setup above); 
endpoint=$(get_endpoint archive)

# Set paths 
remote_base_dir="/group_name/project_name/data/"
output_dir="/project_name/raw_data"
output_file="${output_dir}/fastq_sizes_human_readable.txt"
sample_list="sample_ids.txt"   
# List of Sample IDs (one per line); use only to limit recall to a subset. Leave blank or omit this file to include all samples.

mkdir -p "$output_dir"

# Function to convert bytes to human-readable format
bytes_to_human() {
    b=${1:-0}; d=''; s=0; S=(Bytes {K,M,G,T,E,P,Y,Z}B)
    while ((b >= 1024 && s < ${#S[@]}-1)); do
        d=$(echo "scale=2; $b / 1024.0" | bc)
        b=${d%.*}
        ((s++))
    done
    echo "$d ${S[$s]}"
}

# Initialize output and total size variable
echo "File sizes (human-readable):" > "$output_file"
total_size=0

# Get recursive listing, filter for files, and write file sizes to output
globus ls -rl "$endpoint:$remote_base_dir" | \
    { 
      if [ -f "$sample_list" ]; then
          grep -Ff "$sample_list" | grep '/FASTQ/' | grep 'file'
      else
          grep '/FASTQ/' | grep 'file'
      fi
    } | \
    while IFS= read -r line; do
        size_bytes=$(echo "$line" | awk -F '|' '{print $4}' | xargs)
        file_path=$(echo "$line" | awk -F '|' '{print $7}' | xargs)
        full_path="$remote_base_dir$file_path"
        total_size=$((total_size + size_bytes))
        human_size=$(bytes_to_human $size_bytes)
        echo "$human_size $full_path" >> "$output_file"
    done

total_human_size=$(bytes_to_human $total_size)
echo -e "\nTotal size: $total_human_size" >> "$output_file"
echo "Directory size calculation complete. Results saved to $output_file."
```

Sample output file:

```
File sizes (human-readable):
2.1 GB /group_name/project_name/data/Sample01/FASTQ/sample01_R1.fastq.gz
2.0 GB /group_name/project_name/data/Sample01/FASTQ/sample01_R2.fastq.gz
1.9 GB /group_name/project_name/data/Sample02/FASTQ/sample02_R1.fastq.gz
2.2 GB /group_name/project_name/data/Sample02/FASTQ/sample02_R2.fastq.gz

Total size: 8.2 GB
```

## Usecase 2: Selective recall across many samples

After estimating file sizes, I use the summary file to prepare a batch transfer file for `globus-cli`. This lets me move only what I need, wherever I need it. 

Script for generating batch file:

```bash
#!/bin/bash

# Set paths
project_dir="/project_name/raw_data"
input_file="${project_dir}/fastq_sizes_human_readable.txt"
output_file="${project_dir}/globus_batch.txt"

# Associative array to prevent duplicate batch lines 
declare -A processed_samples

> "$output_file"

while IFS= read -r line; do
    # Skip headers/summaries
    [[ "$line" =~ ^(File\ sizes|Total\ size|$) ]] && continue
    # Extract file path 
    path=$(echo "$line" | sed 's/^[^ ]* [^ ]* //')
    # Get sample name from path 
    if [[ "$path" =~ /([A-Za-z0-9_-]+)/FASTQ/ ]]; then
        sample="${BASH_REMATCH[1]}"
    else
        continue
    fi
    # Avoid redundant batch lines per sample
    fastq_dir=$(echo "$path" | grep -o ".*/FASTQ")
    [[ -z "$fastq_dir" || -n "${processed_samples[$fastq_dir]}" ]] && continue
    processed_samples[$fastq_dir]=1
    dest_dir="${project_dir}/${sample}/FASTQ/"
    echo "--recursive $fastq_dir $dest_dir" >> "$output_file"
done < "$input_file"

echo "Globus batch file created at $output_file."
```

Sample `globus_batch.txt` output:

```
--recursive /group_name/project_name/data/Sample01/FASTQ /project_name/raw_data/Sample01/FASTQ/
--recursive /group_name/project_name/data/Sample02/FASTQ /project_name/raw_data/Sample02/FASTQ/
--recursive /group_name/project_name/data/Sample03/FASTQ /project_name/raw_data/Sample03/FASTQ/
```

Submit the recall request using `globus-cli`:

```bash
module load globus-cli

# Launch the transfer and capture ID
TASK_ID=$(globus transfer --batch "$(get_endpoint archive)" "$(get_endpoint cluster_1)" < /project_name/raw_data/globus_batch.txt | awk '/Task ID:/ {print $3}')
echo "Submitted Globus transfer with Task ID: $TASK_ID"

# Track transfer status
globus task show $TASK_ID
```

{: .box-note}
**Tip**: For large transfers, consider running this command as a Slurm job for reliability.

## Usecase 3: Pattern-based file selection

Sometimes I need to recall only certain output files (like summary tables, metrics, or plots) for many samples, rather than all files in each directory. Here is how I automate that.

Assume this is the folder structure in archival storage:

```
/group_name/project_name/data/
├── Sample01/
│   └── pipeline_out/
│        ├── metrics_summary.csv
│        ├── sample01_feature-barcode-matrix.h5
│        ├── web_summary.html
│        ├── genome_bam.bam
│        └── other_output.txt
├── Sample02/
│   └── pipeline_out/
│        ├── metrics_summary.csv
│        ├── sample02_feature-barcode-matrix.h5
│        ├── web_summary.html
│        ├── genome_bam.bam
│        └── other_output.txt
...
```

Script to generate a batch file for just specific file types:

```bash
#!/bin/bash

# Set paths
project_dir="/project_name/raw_data"
input_file="${project_dir}/pipeline_file_sizes.txt"
output_file="${project_dir}/pattern_batch.txt"

# Example patterns for recall
pattern="csv\|h5\|html"  

sample_list="sample_ids.txt"         
# List of Sample IDs (one per line); use only to limit recall to a subset. Leave blank or omit this file to include all samples.

# Assumes get_endpoint() is exported from your shell config (see setup above); 
endpoint=$(get_endpoint archive)
remote_base_dir="/group_name/project_name/data/"

module load globus-cli
globus ls -rl $endpoint:$remote_base_dir > "${input_file}"

> "$output_file"

# Filter and generate pattern based batch file
## Check if sample subset to be processed
if [ -f "$sample_list" ]; then
    cat "$input_file" | grep -Ff "$sample_list" | grep '/pipeline_out/' | grep -E "$pattern" | grep 'file' | \
    while IFS= read -r line; do
        # Extract file path (remove the size field and prefix whitespace)
        path=$(echo "$line" | awk -F'|' '{print $7}' | xargs)
        dest_path="${project_dir}/$(basename "$(dirname "$path")")/pipeline_out/"
        echo "$remote_base_dir$path $dest_path" >> "$output_file"
    done
else
    cat "$input_file" | grep '/pipeline_out/' | grep -E "$pattern" | grep 'file' | \
    while IFS= read -r line; do
        # Extract file path (remove the size field and prefix whitespace)
        path=$(echo "$line" | awk -F'|' '{print $7}' | xargs)
        dest_path="${project_dir}/$(basename "$(dirname "$path")")/pipeline_out/"
        echo "$remote_base_dir$path $dest_path" >> "$output_file"
    done
fi

echo "Pattern-based batch file created at $output_file."

# Submit transfer request
globus transfer --batch "$(get_endpoint archive)" "$(get_endpoint cluster_1)" < "$output_file"
```

Sample `pattern_batch.txt` output:

```
/group_name/project_name/data/Sample01/pipeline_out/metrics_summary.csv /project_name/raw_data/Sample01/pipeline_out/
/group_name/project_name/data/Sample01/pipeline_out/web_summary.html /project_name/raw_data/Sample01/pipeline_out/
/group_name/project_name/data/Sample01/pipeline_out/sample01_feature-barcode-matrix.h5 /project_name/raw_data/Sample01/pipeline_out/
```

{: .box-note}
**Tip**: You can track your job in the Globus web UI or get list of your tasks on cli:
`globus task list`
