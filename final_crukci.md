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

Alignment is still running

Sorting:
```
mkdir sorted_bams
while read -r line; do
    echo "Processing file: $line"
    samtools collate -@ 20 -Ou bams/${line}.bam | samtools fixmate -@ 20 -m - - | samtools sort -@ 20 - -o sorted_bams/${line}.bam
done < pairs.txt
```
