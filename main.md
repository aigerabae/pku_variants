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

Now need to examine the report and see if its good or not. Next step - trimming
#### trimming

for a single pair of files:
```bash
fastp -i 
-I
-o
-O
--thread 20 -g -c -y 30
--html 
--json
--report_title  
```

first identifying file names for each sample
i saved all ids from metadata from xlsx file to samples.tsv in samples folder

```bash
while IFS=$'\t' read -r sample; do
    echo -n "$sample: "
    find FKU-Run-1 -type f -name "*$sample*" -printf "%f " 2>/dev/null
    echo
done < samples/samples.tsv
```

Need to figure out how files map to samples (inconsistent naming); emailed them


After your files have uniform names
```bash
for first in `ls *_1.fastq.gz`;
do
    second=`echo ${first} | sed 's/_1/_2/g'`
    fastp -i ${first} -I ${second} -o ${first}_trimmed.fastq.gz -O ${second}_trimmed.fastq.gz
done
```

#### Source
Follows a tutorial from https://www.protocols.io/view/a-standard-pipeline-for-processing-short-read-sequ-c6ygzftw.pdf
