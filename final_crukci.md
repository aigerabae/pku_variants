<img width="115" height="1212" alt="image" src="https://github.com/user-attachments/assets/8df2b43f-bdbf-4e85-9675-1e328cd1a592" />QC:
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
```

In sample_sheet i made sample_sheet2.tsv with bams_rg instead of sorted_bams
Config file:
```
params {
    samples               = "sample_sheet2.tsv"
    amplicons             = "amplicons.tsv"
    referenceGenomeFasta  = "../ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna"
    vepAnnotation         = true
    vepCacheDir           = "../pku2/crukci_pipeline/vep_cache/"
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

The command:
```
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 -c config.txt -with-docker
```

VEP web interface is giving error so i will run command line version:
```
docker pull ensemblorg/ensembl-vep
docker run -v $(pwd):/data ensemblorg/ensembl-vep vep --database -i /data/rsids.csv -o /data/output.vcf
```

RestAPI Ensembl:
```
curl -s -X POST \
  -H 'Content-type:application/json' \
  -H 'Accept:text/x-vcf' \
  -d '{ "ids": ["rs772897","COSV108133564","rs1522306","COSV61015928","rs1126758","COSV61015935","rs2251905","COSV61016573","rs1718301","COSV61016577","rs2037639","rs1042503","CX056901","CX1618317","COSV61020278","rs2280615","rs17842947","CS135060","COSV61016895","rs1801153","rs2280616","rs62514903","CM930536","rs62508588","CM910283","CM993955","COSV107395880","rs5030861","rs772897","COSV108133564","rs1522306","COSV61015928","rs1126758","COSV61015935","rs2251905","COSV61016573","rs1718301","COSV61016577","rs2037639","rs1042503","CX056901","CX1618317","COSV61020278","rs2280615","rs17842947","CS135060","COSV61016895","rs1801153","rs2280616","rs62514903","CM930536","rs62508588","CM910283","CM993955","CM870016","COSV61018595","rs5030851","CM024140","CM910292","rs62514936","rs62507288","CS930851","CS930852","CS971839","rs5030849","CM910287","CM950891","COSV61020894","rs118092776","CM981427","COSV61020094"] }' \
  'https://rest.ensembl.org/variant_recoder/human?vcf_string=1&fields=hgvsg,hgvsc,hgvsp,spdi,id,synonyms,vcf_string,mane_select' \
  -o output.vcf
```
