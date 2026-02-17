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

Examined the report.


#### renaming 
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

Quality is satisfactory; data behave as expected by the panel targeted sequencing

#### mapping reads with BWA
I downloaded GRCh38 reference genome, version specific for alignment pipelines (from ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz) and indexed it with BWA (runs from ref directory):
Source: https://lh3.github.io/2017/11/13/which-human-reference-genome-to-use

I also downloaded BWA indexed file for it (had to download on a different device because it kept getting corrupted):
https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.bwa_index.tar.gz


I mapped our reads to it (runs from root directory):
```bash
while read -r line; do
    echo "Processing file: $line"
    bwa mem -M -t 20 \
        ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna \
        fastp/${line}R1_trimmed.fastq.gz \
        fastp/${line}R2_trimmed.fastq.gz \
    | samtools view -b -o bams/${line}.bam
done < pairs.txt

```

#### Sorting bam files:
```bash
mkdir bams/sorting
while read -r line; do
    echo "Processing file: $line"
    samtools collate -@ 20 -Ou bams/${line}.bam | samtools fixmate -@ 20 -m - - | samtools sort -@ 20 - -o bams/sorting/${line}.bam
done < pairs.txt
```

To deal with technical replicates I will merge them to increase quality of variant calling. Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC4137624/
```bash
mkdir bams/merged
echo "bams/sorting/control1a.bam
bams/sorting/control1b.bam
bams/sorting/control1c.bam
bams/sorting/control1d.bam
bams/sorting/control1e.bam
bams/sorting/control1f.bam" > files1.txt
samtools merge -b files1.txt -o bams/merged/control1.bam
echo "bams/sorting/control14a.bam
bams/sorting/control14b.bam
bams/sorting/control14c.bam
bams/sorting/control14d.bam
bams/sorting/control14e.bam
bams/sorting/control14f.bam" > files1.txt
samtools merge -b files1.txt -o bams/merged/control14.bam
echo "bams/sorting/control3a.bam
bams/sorting/control3b.bam
bams/sorting/control3c.bam
bams/sorting/control3d.bam
bams/sorting/control3e.bam
bams/sorting/control3f.bam" > files1.txt
samtools merge -b files1.txt -o bams/merged/control3.bam
```

Adding all other files there:
```bash
cp bams/sorting/{case1.bam,case2.bam,case3.bam,case4.bam,case5.bam,case6.bam,case7.bam,case8.bam,case9.bam,case10.bam,control2.bam,control4.bam,control5.bam,control6.bam,control7.bam,control8.bam,control9.bam,control10.bam,control11.bam,control12.bam,control13.bam} bams/merged/
```

I manually edited pairs.txt to remove 1a,1b,1c,etc. and only leave 1,3,14 for merged files

#### Marking duplicates:
```bash
mkdir bams/dups
while read -r line; do
    echo "Processing file: $line"
    samtools markdup -@ 20 -d 100 bams/merged/${line}.bam bams/dups/${line}.bam
done < pairs.txt
```

#### Indexing:
```bash
mkdir bams/flagstat_index
while read -r line; do
    echo "Processing file: $line"
    samtools index -b bams/dups/${line}.bam 
    samtools flagstat bams/dups/${line}.bam  > bams/flagstat_index/${line}.output.flagstat
done < pairs.txt
```

#### Variant calling:
```bash
find bams/dups/ -type f -name "*.bam" > list.txt
mkdir vcf
bcftools mpileup --threads 20 -a FORMAT/AD,FORMAT/DP,FORMAT/SP,INFO/AD --fasta-ref ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna -b list.txt  | bcftools call --threads 20 -f GQ,GP -m -Oz -o vcf/output.vcf.gz
```

QC in plink:
```bash
plink --vcf output2.vcf --make-bed --out test
plink --bfile test --geno 0.02 --make-bed --out test2
plink --bfile test2 --mind 0.02 --make-bed --out test3
plink --bfile test3 --maf 0.0001 --make-bed --out test4
sed 's|bams/dups/||g' test4.fam -i
plink2 --bfile test4 --set-all-var-ids @:# --make-bed --out test5
```

That leaves us with 29 SNPs, all in the region of PAH gene (we removed low quality SNPs, SNPs with high missingness rate, monomorphic SNPs)  

I used test4 to generate annotations with all info available from https://www.snp-nexus.org/v4/results/7ec21dde/ and saved the output info vcf1_vcf/  

#### Source
Follows a pipeline from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf

I used it instead of GATK because this is amplicon sequencing for which GATK is not optimized; it is recommended to use something like mpileup. Source: https://gatk.broadinstitute.org/hc/en-us/community/posts/360057582511-HaplotypeCaller-data-generated-from-amplicon-sequencing
