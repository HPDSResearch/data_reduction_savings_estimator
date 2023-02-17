# Brief Description
A tool to estimate data reduction savings

# Motivation behind developing our data reduction estimator
   Data reduction (usually deduplication and compression) is an important feature in enterprise systems. Considering the high system overheads of inline data reduction, estimating the amount of data reducability provides a strong insight on whether to enable deduplication + compression, deduplication-only, compression-only or none of them! A couple of existing open-source codes estimate data reduction at different layers. However, with two goals on mind, as part of a bigger project in 2021 at HPDS Research, we decided to prepare our own data reduction estimator to be: (1) easily expandable and modifiable, (2) fast, with minimal system resource usage. 
   
   To address the above goals, we have coded an light-weight estimator in Python (rather than C or other difficult-to-debug/develop languages). Furthermore, we have fine-tuned our code to minimize the DRAM/CPU utilization, while providing a decent accuracy and speed.
   
# Brief information about our data reduction estimator

##Inputs/Outputs
   This code receives a block device (or file) name, and the size of valid data in thatdevice. Then it reads the valid data from it, and estimates the amount of compression-only[LZ4] , deduplication-only, and dedup+compression savings with minimal DRAM and CPU usage. Additional important inputs of this code: data reduction block size (e.g., 4096 byte), available DRAM space (MB), type of desired estimation (D, C, DC)


## System Resource Usage

### DRAM Space Usage
 This code keeps all the hash table for deduplication in DRAM, and does not require any separate storage device.
 Based on available DRAM, the usable amount should be provided as input to the code. When the allocated DRAM space is fully used, and new chunk hashes are required to be inserted into the table, hash table would be reset (=cleaning DRAM buffer) and new chunk hashes would be inserted into the clean table. Note that we have minimized the hash table space usage by using 32-bit keys, and fixed (dummy) value as the value in the hash table. 32-bit keys may seem not to support capacities over 16 TB, but as this code estimates deduplication, there is no need to provide exact deduplication, and decent accuracy still is achievable with capacities much larger than 16TB. Overall, we have controlled the DRAM space usage, but depending on the dataset, some trade-off between the deduplication estimation accuracy and the required DRAM space exist. 

### CPU Utilization 
the current code is single threaded for simplicity and also minimizing the CPU utilization in  production environments. However, an optional multi-threaded version is a TODO work.

#Speed Test Examples
 For 1TB block device,
 with 0% compressible or deduplicable data -->  9.2GB RAM usage, estimation run time=90 min
 with 50% compressible and 50% deduplicable data (overall 75% saving) --> 9.2GB RAM usage, estimation run time= 126min


# Developers Info
This data reduction estimator was designed and developped by Mahdi Bahrami and Mohammadamin Ajdari at HPDS Research. It was part of a bigger project which finished in early 2022. As of Feb 2023, we decided to publicly release this code.

# Citation
If you use this code, please cite this repository in the following way:

HPDS Research, Repository of Data Reduction Estimator, "https://github.com/HPDSResearch/data_reduction_savings_estimator", <Last Update Year>

# LICENSING and USAGE
Please refer to USAGE file. A very brief description is as follows:
This piece of software can be used free of charge for both academic and commercial purposes.
If you modify the code, the original list of developpers must accompany your code.

If you require any professional support or special customization on the code for your environment, please send an email to ajdari@hpds.ir  .




