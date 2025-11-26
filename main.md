#### envs and installation
```bash
conda create -n pku python=3.9
conda activate pku
conda install multiqc
conda install bioconda::fastqc
```

#### fastqc
```bash
fastqc -t 24 FKU-Run-1/*fastq.gz* -o fastqc_output
```

#### multiqc 
```bash
multiqc fastqc_output -o multiqc_output -n pku
```

Now need to examine the report and see if its good or not. Next step - renaming files and trimming


#### renaming 
Need to figure out how files map to samples (inconsistent naming); emailed them
I made a file rename.txt with old names and new names with consistent naming scheme and renamed all files using this dictionary (runs from FKU-Run-1 folder):
```bash
while IFS=$'\t' read -r old new; do [ -f "$old" ] && mv "$old" "$new"; done < ../rename.txt
```

#### trimming with fastp
I then created a file pairs.txt that contained the root of the filenames for pairs (ie case1 for case1_R1.fastq.gz and case1_R2.fastq.gz) and iterated with fastp on that list (files are in FKU-Run-1, and rename.txt and pairs.txt are in directory up (../) (runs from FKU-Run-1 folder):
```bash
for line in $(cat ../pairs.txt); do
    echo "Processing line: $line"
    fastp -i ${line}_R1.fastq.gz -I ${line}_R2.fastq.gz -o ../fastp/${line}R1_trimmed.fastq.gz -O ../fastp/${line}R2_trimmed.fastq.gz --thread 20 -g -c -y 30 
done
```

Checking if quality improved (runs from fastp directory):
fastqc again:
```bash
cd fastp
fastqc -t 24 *fastq.gz* -o fastqc2/
multiqc ./ -o multiqc_output -n pku2
```

Per base sequence quality tells you if there was any systematic drop in quality during cycles, this is an important metric, and mine is ok.  
Per sequence quality scores tells you if there's a group of sequences that have an overall low quality, also important, mine is ok.  
! Per base sequence content might fail because of some nonrandom distribution in the first bases. Often due to technical quirks and not a huge problem, especially if really only in the initial bases (in our case).   
! Per sequence GC content isn't expected to pass in exomes or gene panels. Should pass for genomes.  
Per base N content tells you if there's any hard-to-call position in reads, if it fails it can be due to a sequencing issue, mine is ok.  
! Sequence length distribution should pass for untrimmed reads, mine are trimmed so it's expected that not all of them have the same length.  
! Sequence duplication levels - depends on the methods. If it's a gene panel where each base was sequenced 500x, then you're going to have some duplicated sequences and it's ok. Transcriptomes also are ok with some duplication. Amplicon sequencing (Ampliseq) also gets flagged here but it's ok. If it's a genome or an exome performed with hybrid capture, then this should pass, if there's duplications it might indicate that the starting library was too diluted pre-amplification, you could lose variants even with somehow decent coverage.  
Adapter content should pass too, and mine does.  
!!! Overrepresented sequences - doesn't pass; possibly because of extremely high duplication levels

Source: https://www.reddit.com/r/bioinformatics/comments/1et5gt7/fastqc_evaluation_parameters_for_variant_calling/
#### mapping reads with BWA
I downloaded RefSeq GRCh38.p14 reference genome and indexed it with BWA (runs from ref directory):
```bash
bwa index GCF_000001405.40_GRCh38.p14_genomic.fna
```

I mapped our reads to it (runs from root directory):
```bash
for line in $(cat ../pairs.txt); do
    echo "Processing file: $line"
    bwa mem \
    -M -t 20\
    ref/GCF_000001405.40_GRCh38.p14_genomic.fna \ # reference genome
    fastp/${line}R1_trimmed.fastq.qz \ # trimmed forward reads
    fastp/${line}R2_trimmed.fastq.qz |\ # trimmed reverse reads
    samtools view -b > bams/{line}.bam
done
```


To deal with technical replicates I will merge them to increase quality of variant calling. Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC4137624/


#### Source
Follows a tutorial from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf
