#### envs and installation
```bash
conda create -n pku python=3.5
conda activate pku
conda install multiqc
conda install fastp
conda install samtools=1.9
conda install bioconda::fastqc
conda install bwa
conda activate pku
```

#### fastqc
```bash
fastqc -t 24 files/*001.fastq.gz* -o fastqc_output
```

#### multiqc 
```bash
multiqc fastqc_output -o multiqc_output -n pku
```

Examined the report.

#### trimming with fastp
I then created a file pairs.txt that contained the root of the filenames for pairs (ie case1 for case1_R1.fastq.gz and case1_R2.fastq.gz) and iterated with fastp on that list (files are in FKU-Run-1, and rename.txt and pairs.txt are in directory up (../) (runs from FKU-Run-1 folder):
```bash
for line in $(cat pairs.txt); do
    echo "Processing line: $line"
    fastp -i files/${line}R1.fastq.gz -I files/${line}R2.fastq.gz -o fastp/${line}R1_trimmed.fastq.gz -O fastp/${line}R2_trimmed.fastq.gz --thread 20 -g -c -y 30 
done
```

Checking if quality improved (runs from fastp directory):
fastqc again:
```bash
cd fastp
mkdir fastqc2
fastqc -t 24 *fastq.gz* -o fastqc2/
mkdir multiqc_output
multiqc fastqc2/ -o multiqc_output -n pku2
cd ../
```

Quality is satisfactory; data behave as expected by the panel targeted sequencing

#### mapping reads with BWA
I downloaded GRCh38 reference genome, version specific for alignment pipelines (from ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz) and indexed it with BWA (runs from ref directory):
Source: https://lh3.github.io/2017/11/13/which-human-reference-genome-to-use

I also downloaded BWA indexed file for it (had to download on a different device because it kept getting corrupted):
https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.bwa_index.tar.gz


I mapped our reads to it (runs from root directory):
```bash
mkdir bams/
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

#### Marking duplicates:
```bash
mkdir bams/dups
while read -r line; do
    echo "Processing file: $line"
    samtools markdup -@ 20 bams/sorting/${line}.bam bams/dups/${line}.bam
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
find /media/aygera/external_disk/biostar/NCB/PKU/bams/dups/ -type f -name "*.bam" > list1.txt
find /media/aygera/external_disk/biostar/NCB/pku2/bams/dups/ -type f -name "*.bam" > list2.txt
cat list1.txt > list.txt
cat list2.txt >> list.txt
mkdir vcf
bcftools mpileup --threads 20 -a FORMAT/AD,FORMAT/DP,FORMAT/SP,INFO/AD --fasta-ref ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna -b list.txt  | bcftools call --threads 20 -f GQ,GP -m -Oz -o vcf/output.vcf.gz
```

Next step here:
QC in plink:
```bash
cd vcf
gunzip -c output.vcf.gz > output2.vcf
plink --vcf output2.vcf --make-bed --double-id --out test
plink --bfile test --geno 0.02 --make-bed --out test2 --double-id
plink --bfile test2 --mind 0.02 --make-bed --out test3 --double-id
plink --bfile test3 --maf 0.0001 --make-bed --out test4 --double-id
sed 's|/media/aygera/external_disk/biostar/NCB/pku2/||g' test4.fam -i
sed 's|/media/aygera/external_disk/biostar/NCB/PKU/||g' test4.fam -i
sed 's|bams/dups/||g' test4.fam -i
sed 's|_||g' test4.fam -i
sed 's|.bam||g' test4.fam -i
plink2 --bfile test4 --set-all-var-ids @:# --make-bed --out test5
plink2 --bfile test5 --export vcf --out test5
```

That leaves us with 53 SNPs, all in the region of PAH gene (we removed low quality SNPs, SNPs with high missingness rate, monomorphic SNPs)  

I used test5 to generate annotations with all info available from https://www.snp-nexus.org/v4/

#### Source
Follows a pipeline from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf
