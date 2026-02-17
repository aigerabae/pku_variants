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
