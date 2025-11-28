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
I downloaded GRCh38 reference genome, version specific for alignment pipelines (from ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz) and indexed it with BWA (runs from ref directory):
Source: https://lh3.github.io/2017/11/13/which-human-reference-genome-to-use

I also downloaded BWA indexed file for it (had to download on a different device because it kept getting corrupted):
https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.bwa_index.tar.gz


After it finished downloading, I will try this command (first extracted the bwa index tarball into the folder)
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

I have vcf file. Next steps - QC and analysis.   

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

I manually added 1 for controls and 2 for cases in test4.fam to differentiate between cases and controls  
I also used test4 to generate annotations with all info available from https://www.snp-nexus.org/v4/results/7ec21dde/ and saved the output info vcf1_vcf/  

```bash
plink --bfile test5 --model --allow-no-sex  
```

There are 4 SNPs with p<0.05 (some are repeated bc it used several models to test):    
|CHR   |             SNP | A1 | A2 |   TEST   |      AFF  |        UNAFF   |     CHISQ  |   DF |          P   |
|------|-----------------|----|----|----------|-----------|----------------|------------|------|--------------|
|  12  | 12:102866600    | A  |  G | TREND    |     4/16  |        0/28    |    6.72    |  1   |   0.009534   |
|  12  | 12:102866600    | A  |  G | ALLELIC  |     4/16  |        0/28    |    6.109   |  1   |   0.01345    |
|  12  | 12:102852929    | T  |  C | TREND    |     5/15  |        1/27    |    5.714   |  1   |   0.01683    |
|  12  | 12:102852929    | T  |  C | ALLELIC  |     5/15  |        1/27    |    4.898   |  1   |   0.02689    |
|  12  | 12:102852815    | A  |  G | TREND    |     3/17  |        0/28    |    4.8     |  1   |   0.02846    |
|  12  | 12:102894812    | A  |  G | TREND    |     3/17  |        0/28    |    4.8     |  1   |   0.02846    |
|  12  | 12:102852815    | A  |  G | ALLELIC  |     3/17  |        0/28    |    4.48    |  1   |   0.03429    |
|  12  | 12:102894812    | A  |  G | ALLELIC  |     3/17  |        0/28    |    4.48    |  1   |   0.03429    |


Searching for those SNPs in annotation folder:  
grep "12:102866600" vcf1_vcf/*  
grep "12:102852929" vcf1_vcf/*  
grep "12:102852815" vcf1_vcf/*  
grep "12:102894812" vcf1_vcf/*  

Showed that 3/4 are likely deleterious by SIFT and Polyphen  

plink --bfile test5 --freq case-control --out counts --allow-no-sex

All SNPs where MAF for cases is higher than for controls
  12   12:102851701    A    C          0.1            0         20         28  
  12   12:102852815    A    G         0.15            0         20         28  
  12   12:102866599    T    C          0.1            0         20         28  
  12   12:102866600    A    G          0.2            0         20         28  
  12   12:102866641    T    C          0.1            0         20         28  
  12   12:102894812    A    G         0.15            0         20         28  
  12   12:102917377    A    G            0      0.03571         20         28  
  12   12:102852929    T    C         0.25      0.03571         20         28  

  12   12:102840330    T    G         0.15       0.1071         20         28  
  12   12:102843690    G    C          0.2       0.1071         20         28  
  12   12:102851799    G    T          0.3       0.1786         20         28  
  12   12:102852590    T    C          0.4       0.3571         20         28  
  12   12:102852868    T    G         0.15       0.1071         20         28  
  12   12:102877415    A    G         0.45       0.3214         20         28  
  12   12:102912772    G    A          0.1      0.07143         20         28  
  12   12:102917009    A    G         0.35       0.2143         20         28  
  12   12:102917201    G    T          0.2       0.1071         20         28  


#### Source
Follows a tutorial from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf
