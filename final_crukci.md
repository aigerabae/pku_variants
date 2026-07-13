QC:
```
conda activate fastqc
fastqc input/**
mkdir fastqc
find ./input -maxdepth 1 -type f ! -name "*.gz" -exec mv {} ./fastqc \;
multiqc fastqc/
```

Trimming adapters:
```
ls input/ | sed 's/.\{16\}$//' | uniq > pairs.txt
mkdir trimmed
for line in $(cat pairs.txt); do
    echo "Processing line: $line"
    fastp -i input/${line}_R1_001.fastq.gz -I input/${line}_R2_001.fastq.gz -o ./trimmed/${line}_R1_trimmed.fastq.gz -O ./trimmed/${line}_R2_trimmed.fastq.gz --thread 20 -g -c -y 30 
done
```

Alignment:
```
conda activate samtools
mkdir bams
while read -r line; do
    echo "Processing file: $line"
    bwa mem -M -t 20 \
        ~/biostar/NCB/pku2/ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna \
        trimmed/${line}_R1_trimmed.fastq.gz \
        trimmed/${line}_R2_trimmed.fastq.gz \
    | samtools view -b -o bams/${line}.bam
done < pairs.txt
```

Sorting:
```
mkdir sorted_bams
while read -r line; do
    echo "Processing file: $line"
    samtools collate -@ 20 -Ou bams/${line}.bam | samtools fixmate -@ 20 -m - - | samtools sort -@ 20 - -o sorted_bams/${line}.bam
done < pairs.txt
```

I made a sample_sheet.tsv file using those bams and used amplicon file from the previous run

Didn't do this yet, need to adjust code:
Adding @RG:SM tag in bam files:
```
conda activate picard
mkdir -p bams_rg
while IFS=$'\t' read -r LIB SAMPLE BAM; do
    echo "Processing $LIB ($SAMPLE)"
    picard AddOrReplaceReadGroups \
        -I "$BAM" \
        -O "bams_rg/${LIB}.bam" \
        -RGID "$LIB" \
        -RGLB "$LIB" \
        -RGPL ILLUMINA \
        -RGPU "$LIB" \
        -RGSM "$SAMPLE"m
done < sample_sheet.tsv

conda activate samtools
for i in bams_rg/*.bam; do samtools index "$i"; done
cp input/sample_sheet.tsv bams_rg/
cp input/amplicons.tsv bams_rg/
cp input/config.txt bams_rg/
mv input/ unnamed_input/
mv bams_rg/ input/
```

Config file:
```
params {
    samples               = "sample_sheet.tsv"
    amplicons             = "amplicons.tsv"
    referenceGenomeFasta  = "../ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna"
    vepAnnotation         = true
    vepCacheDir           = "~/biostar/NCB/pku2/crukci_pipeline/vep_cache/"
    vepSpecies            = "homo_sapiens"
    vepAssembly           = "GRCh38"
    outputDir             = "results"
    variantCaller         = "HaplotypeCaller"
    minimumAlleleFraction = 0.01
}

profiles {
    myprofile {
        process.executor = 'local'
        executor {
            cpus = 20
            memory = 32.GB
        }
        docker.enabled = true
    }
}
```
