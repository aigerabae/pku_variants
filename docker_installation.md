Installing docker:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
```

Adding user to docker (permission error fix):
```bash
sudo groupadd docker
sudo usermod -aG docker ${USER}
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart docker
```

Installing GATK haplotypecaller via docker:
```bash
docker pull broadinstitute/gatk
```

Running haplotypecaller (not customized, just example command):
```bash
 gatk --java-options "-Xmx4g" HaplotypeCaller  \
   -R Homo_sapiens_assembly38.fasta \
   -I input.bam \
   -O output.g.vcf.gz \
   -ERC GVCF
```

Installing Java:
```bash
sudo apt install default-jre
```

Installing nextflow:
```bash
#First you will need to ensure that you have at least version 8 of java installed. You can check which version you have by typing the following on your command line:
java -version
# if all good - install
curl -fsSL get.nextflow.io | bash
sudo mv nextflow /usr/local/bin
# might need to do this is nextflow doesn't work:
# sudo chmod 715 /usr/local/bin/nextflow 
```

Installing cruk-ci ampliseq pipeline: https://github.com/crukci-bioinformatics/ampliconseq?tab=readme-ov-file#introduction   
```bash
nextflow pull crukci-bioinformatics/ampliconseq -r 1.0
# not required, is supposed to be done by nextflow but i did it anyway:
# docker pull crukcibioinformatics/ampliconseq
```

Running cruk-ci ampliseq pipeline: https://github.com/crukci-bioinformatics/ampliconseq?tab=readme-ov-file#introduction  
```bash
mkdir /mnt/harddisk/biostar/NCB/pku2/crukci_pipeline/vep_cache
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 \
     -main-script download_vep_cache.nf \
     -with-docker \
     --vepCacheDir /mnt/harddisk/biostar/NCB/pku2/crukci_pipeline/vep_cache \
     --vepSpecies homo_sapiens \
     --vepAssembly GRCh38

# it didn't download cash so I downloaded it manually:
curl -O https://ftp.ensembl.org/pub/release-115/variation/indexed_vep_cache/homo_sapiens_vep_115_GRCh38.tar.gz

# didn't do yet
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 \
     -config ampliconseq.config \
     -with-singularity \
     -profile bigserver \
     -with-report ampliconseq_report.html \
     -with-timeline ampliconseq_timeline.html
```

Need to prepapre config file, amplicon file, and sample sheet.

```bash
docker run -it -v ~/biostar/NCB/pku2/:/home crukcibioinformatics/ampliconseq bash
cd home/crukci_pipeline/
curl -fsSL get.nextflow.io | bash
mv nextflow /usr/sbin
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 -c input/config.txt
```

What I had to do manually:
1) i copied sorted bam files from pku1 and pku2 launces into input folder (I initially used unsorted and that didn't work well)
2) i had to add paths to those bam files in sample sheets
3) i duplicated dict file in ref genome and renamed it to have the same name as main ref file
4) changed chromosomes in amplicon file to chr12 instead of just 12
5) i initially copied ref file into input folder but it also needs indexing and other files (like fai, etc.) so i changed directory to the one containing all ref files from previous analysis
6) do sorted bam file indexing in input folder
I did it outside of that docker container because it didn't have conda:
```bash
conda create --override-channels -c conda-forge -c bioconda -c default -n samtools samtools
conda activate samtools
for i in *.bam; do samtools index "$i"; done
```
7) change ref genome version in config file to grch38  
8) after i downloaded vep chache manually i added directory of vep cache to config file
9) i added profile to config file to allocate 30 gb of memory and 20 cpus to the process
10)  unzip vep cache in vep chache folder
```bash
tar -xvzf homo_sapiens_vep_115_GRCh38.tar.gz
```

Resuming after error:
```bash
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 -c input/config.txt -resume
```



I could also run it outside of container like this but it has an issue with system permissions this way so i decided to keep using it in side docker
```bash
nextflow run crukci-bioinformatics/ampliconseq -r 1.0 -config input/config.txt -with-docker
```


Config file:
```
params {
    samples               = "input/sample_sheet.tsv"
    amplicons             = "input/amplicons.tsv"
    referenceGenomeFasta  = "../ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna"
    vepAnnotation         = true
    vepCacheDir           = "vep_cache/"
    vepSpecies            = "homo_sapiens"
    vepAssembly           = "GRCh38"
    outputDir             = "results"
    variantCaller         = "vardict"
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

It worked! I have a file with variants per individual, not exactly a vcf but I should make some use of it. annotation stats are also quite impressive
One thing to keep in mind is that i used vardict variant caller which is more commonly used for somatic mutations, although it is employed for germline variants too. might want to rerun with HaplotypeCaller in config file
