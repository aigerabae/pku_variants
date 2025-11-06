conda create -n pku python=3.9
conda activate pku
conda install multiqc
conda install bioconda::fastqc

# fastqc
fastqc -t 24 FKU-Run-1/*fastq.gz* -o fastqc_output

# multiqc 
multiqc fastqc_output -o multiqc_output -n pku

Now need to examine the report and see if its good or not. Next step - trimming

Follows a tutorial from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf
