---
layout: post
title: The Hidden Bottleneck of Sparse Assignment
subtitle: Lessons from single-cell downsampling workflow
tags: [R, Python, sparse matrices]
comments: true
---

While working on downsampling of a single-cell (sc) dataset i.e., performing binomial thinning on raw UMI counts across matrices of 17,000 genes by 150,000 cells (2.55 billion entries, ~127 million nonzero elements at 5% sparsity), I expected that updating the data in place, chunk by chunk, would be straightforward and efficient. Instead, I quickly discovered a major bottleneck: in-place mutation of large sparse matrices is dramatically slower and more memory-hungry than anticipated. The challenge isn’t unique to my dataset size but in fact, this bottleneck only worsens as matrices grow, turning a seemingly simple operation into a significant limitation.

Here, I document my attempts, what succeeded, what failed, and the practical lessons learned along the way.

# Reality Check of Sparse Matrix Assignment in R

My first approach was to use R for binomial thinning on my large sc matrix, leveraging its widely-used sparse matrix representations (`dgCMatrix`). At first, looped assignment or chunked in-place mutation seemed promising, but the details revealed several critical performance traps. Here's all that I tried:

## Column-wise assignment

This approach updates the matrix by assigning each modified column back to its original location, one at a time.

```R
for (j in chunk_indices) {
    counts[, j] <- downsampled_cols[[j]]
}
```

## Block assignment and *de novo* build

This approach assembles chunks of columns by building blocks using `cbind` and by constructing a new matrix from blocks built up from the data.

```R
chunk_mat <- do.call(cbind, downsampled_cols)
downsmpl_mat <- Matrix::Matrix(0, nrow = nrow(counts), ncol = ncol(counts), sparse = TRUE)
downsmpl_mat[, chunk_indices] <- chunk_mat
```

## Triplet build and convert

Here, the matrix is assembled in triplet (coordinate) form (`dgTMatrix`), allowing for easier incremental construction, and then converted to compressed column format at the end.

```R
triplet <- as.data.frame(summary(as(chunk_mat, "dgCMatrix")))
triplet$j_full <- chunk_indices[triplet$j]
downsmpl_mat <- Matrix::sparseMatrix(
  i = triplet$i,
  j = triplet$j_full,
  x = triplet$x,
  dims = c(n_genes, n_cells)
)
```

## Benchmark

I performed benchmarks using `bench::mark()` on a representative chunk of 100 columns from my sc data matrix, measuring both execution time and peak memory usage for each method.

| Method                                 | Median Time | Memory Allocated | Description                                  |
|-----------------------------------------|-------------|------------------|----------------------------------------------|
| Column-wise assignment                  | 9.19 sec    | 299 MB           | One-at-a-time assignment of columns          |
| Block assignment + *de novo* build        | 9.02 sec    | 21.1 MB          | Assigns all columns of a block in one go     |
| Triplet (COO) build and convert         | 0.025 sec   | 24.3 MB          | Builds using (i, j, x) triplets and converts |

The triplet method is over 350× faster than either block or column-wise assignment and significantly more memory efficient. For large-scale sparse matrix assembly in R, always prefer triplet construction with a one-step conversion to compressed format.

## Why is sparse matrix assignment so painful in R?

Despite being a vital data structure for high-dimensional analyses, R's sparse matrices turn routine assignment into a surprising bottleneck. Here is why:

* **Inefficient under the hood:**
`dgCMatrix` uses a compressed sparse column (CSC) format. Every time a column is assigned, the entire sparse structure needs to be reshuffled, re-indexed, and sometimes fully copied. This makes repeated assignments extremely slow and memory-hungry, especially for large matrices.

* **Always single-threaded:**
Assignment is always limited to a single core in R which is by design. Thus, updates to a sparse matrix cannot be safely performed in parallel. R prevents multiple cores from writing to the same matrix at once to avoid data corruption, so adding more CPUs will not speed up assignment.

* **Optimized for matrix algebra, not assignment:**
Libraries like `Matrix` or backends like `OpenBLAS/MKL` in R are optimized for high-performance matrix algebra (multiplication, decomposition, solving, etc.), but not for assignment or structural changes. In-place edits get none of these speedups.

## Can you use out-of-core approaches to bypass the problem ?

Curious whether out-of-core solutions could speed up sparse matrix mutation, I tested `DelayedArray` and `HDF5Array` to write data in chunks to disk. My workflow was:

```R
library(DelayedArray)

# Create a disk-backed sink with the original dimensions
sink <- HDF5RealizationSink(dim = c(n_genes, n_cells), type = "double", filepath = "out_matrix.h5")

for (i in seq_along(chunk_files)) {
  chunk_mat <- readRDS(chunk_files[i])

  # Must convert sparse dgCMatrix to dense before assignment
  dense_chunk <- as.matrix(chunk_mat)
  
  # Figure out which columns in the full matrix this chunk fills
  col_indices <- chunks[[i]]
  
  # Write the chunk to the sink (disk)
  sink[, col_indices] <- dense_chunk
}

# Finalize (realize) a DelayedArray object from the sink
final_mat_delayed <- realize(sink)
```

**Key limitations**

* Dense conversion required: Each sparse chunk (`dgCMatrix`) had to be converted to dense before writing, causing major RAM spikes and eliminating the potential scalability and speed benefits for large, sparse data.

* No persistent row/column names: HDF5Array does not save row or column names with the data. I had to restore them manually after loading.

* Single-core bottleneck: Assignment and disk I/O still used just one CPU core, with no speed gain from parallelization, so mutation remained slow despite using disk.

# Fast Sparse Mutation vs AnnData/Scanpy Compatibility

Python’s `scipy.sparse` LIL (List of Lists) and DOK (Dictionary of Keys) formats are optimized for efficient, rapid in-place sparse matrix mutation all while restricted to single core. This makes large-scale updates (e.g., replacing 120k columns in a 17k × 150k matrix in ~10 minutes) not just possible, but practical. However, there are important limitations for single-cell workflows using AnnData or Scanpy.

## AnnData (Scanpy) warning for LIL/DOK 

Since AnnData 0.12, attempts to assign or export a LIL/DOK matrix to `.X` trigger a warning.

```Python
FutureWarning: AnnData previously had undefined behavior around matrices of type <class 'scipy.sparse._lil.lil_matrix'>. In 0.12, passing in this type will throw an error. Please convert to a supported type. Continue using for this minor version at your own risk.
```

## Why this limitation ?

LIL and DOK formats are efficient for in-place construction and mutation, but not for downstream matrix algebra, chunked disk storage, or persistent `.h5ad` files. CSR and CSC formats are the industry standard for scalable on-disk storage, linear algebra, and interoperability.

## Recommended workflow

Convert the count matrix to LIL (or DOK) only for mutation/construction steps and revert back to the default CSR or CSC format for standard workflow steps. 

```Python
# Convert to LIL for mutation
adata.X = adata.X.tolil()   

... # Perform in-place edits

# Convert back to CSR format prior to saving/analysis
adata.X = adata.X.tocsr()  
```

{: .box-note}
**Tip:** Never store or save an AnnData/Scanpy object with `.X` in LIL/DOK format.

# Takeaways

Downsampling large sc matrices is a tempting way to equalize sequencing depth, but the technical bottlenecks, especially for in-place sparse assignment are substantial. 
Even in popular tools like Seurat or Scanpy, built-in downsampling functions are primarily designed for simulation, benchmarking, or sanity checks and not as a standard preprocessing strategy. Statistical modeling and regression approaches to account for depth bias or technical covariates are typically more robust, reproducible, and recommended than aggressive downsampling. However, if you do need to downsample:

**R**: build the matrix *de novo* using the triplet (`dgTMatrix`) format for efficient construction and conversion

**Python**: leverage the LIL format for fast batch assignment but convert back to CSC/CSR for downstream analysis


