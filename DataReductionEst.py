#!/usr/bin/env python3

############################################
#Designed and developped by Mahdi Bahrami and Mohammadamin Ajdari at HPDS Research.

#Mahdi Bahrami: https://www.linkedin.com/in/mahdibahrami/
#Mohammadamin Ajdari: https://www.linkedin.com/in/mohammadamin-ajdari-a392a5110/


###### General Info ####

#   This code receives a block device (or file) name, and the size of valid data in that
#   device. Then it reads the valid data from it, and estimates the amount of compression-only[LZ4]
#  , deduplication-only, and dedup+compression savings with minimal DRAM and CPU usage.
# Additional important inputs of this code: data reduction block size (e.g., 4096 byte), available DRAM space (MB),
# type of desired estimation (D, C, DC)
#########################


######## DRAM Space Usage #####
# This code keeps all the hash table for deduplication in DRAM, and does not require any separate storage device.
# Based on available DRAM, the usable amount should be provided as input to the code.
# When the allocated DRAM space is fully used, and new chunk hashes are required to be inserted into the table,
# hash table would be reset (=cleaning DRAM buffer) and new chunk hashes would be inserted into the clean table.
# Note that we have minimized the hash table space usage by using 32-bit keys, and fixed (dummy) value as the value
# in the hash table. 32-bit keys may seem not to support capacities over 16 TB, but as this code estimates deduplication 
#, there is no need to provide exact deduplication, and decent accuracy still is achievable with capacities much larger than 16TB.
# Overall, we have controlled the DRAM space usage, but depending on the dataset, some trade-off between the deduplication estimation accuracy and
# the required DRAM space exist. 

########## CPU Utilization #####
# the current code is single threaded for simplicity and also minimizing the CPU utilization in 
#production environments. However, an optional multi-threaded version is a TODO work.
################################

#### Speed Test Examples #####
#For 1TB block device,
#with 0\% compressible or deduplicable data -->  9.2GB RAM usage, estimation run time=90 min
#with 50\% compressible and 50\% deduplicable data (overall 75\% saving) --> 9.2GB RAM usage, estimation run time= 126min

##########################






import os 
import mmh3
import lz4.frame
import sys
import json

hash_table = {}
"""hash table is a dic by this format: key=hash of data , value=0"""

def main():
    if len((sys.argv)) < 5:
#   To select the type of estimation desired, one of the following characters should be given
#   as input when this script runs.
#     C:  for compression-only estimation
#     D: for deduplication-only estimation
#     DC: for deduplication+compression estimation
 
        print("input parametr not enogh \n/\
        the currect input format must be like this\
        :\n 1-EstimateType(D,C,DC)  2-BlkDevicePath(/dev/sdXX)\
        3-BlkDeviceSize(GB)  4-UnitSize(B)  5-limit of ram usage(MB)\n")
        print("Example: DC /dev/sdb 100 4096 1024\n")

        return

    estimate_type = sys.argv[1]
    Blk_Device = sys.argv[2]
    Blk_Device_size = int(sys.argv[3])
    unit_size = int(sys.argv[4])
    ram_limit = int(sys.argv[5])
    Blk_Device = open(Blk_Device, 'rb')
    block_count = int(Blk_Device_size * 1024 * 1024 * 1024 / (unit_size))

    estimate_swticher = {
        "D": {
            "function": estimate_dedup,
            "args": {
                "block_count": block_count,
                "ram_limit": ram_limit,
                "Blk_Device": Blk_Device,
                "unit_size": unit_size
            }
        },
        "C": {
            "function": estimate_compression,
            "args": {
                "block_count": block_count,
                "Blk_Device_size": Blk_Device_size,
                "Blk_Device": Blk_Device,
                "unit_size": unit_size
            }
        },
        "DC": {
            "function": estimate_dedup_compression,
            "args": {
                "block_count": block_count,
                "Blk_Device_size": Blk_Device_size,
                "ram_limit": ram_limit,
                "Blk_Device": Blk_Device,
                "unit_size": unit_size
            }
        },
    }

    if estimate_type not in estimate_swticher.keys():
        raise Exception("type not fond!!!")

    estimate_swticher[estimate_type]["function"](
        **estimate_swticher[estimate_type]["args"]
    )


def estimate_dedup_compression(block_count, ram_limit, Blk_Device, Blk_Device_size, unit_size):
    comp_len_kb = 0.0
    dedu_comp = 0
    saved_block = 0
    for block_counter in range(0,block_count):

        if block_counter % 100000 == 0:
            ramsize = ( sys.getsizeof(hash_table) / 1024) / 1024
            if int(ramsize) > ram_limit:
                print('hash table flushed')
                hash_table.clear()

        Blk_Device.seek(block_counter * unit_size)
        chunk = Blk_Device.read(unit_size)


        #estimate compression
        chunk_len = len(chunk)
        # length of block after compress
        comp_len = len(lz4.frame.compress(chunk))
        if (comp_len > chunk_len ):
            comp_len = chunk_len

        comp_len_kb += ((comp_len / 1024))
        comp_len_kb = round(comp_len_kb, 4)

        #estimate dedup
        if if_exist(chunk):
            saved_block = saved_block + 1
        # if data is uniq
        else:
            dedu_comp = dedu_comp + comp_len
            add_to_hash_table(chunk)

    duplicate_percentage = (saved_block / block_count) * 100
    duplicate_amount = (((saved_block * unit_size) / 1024) / 1024) / 1024
    output_dict = {
        'Deduplication saving (%)': duplicate_percentage,
        'Deduplication saving (GB)': duplicate_amount
    }

    # compression percentage
    c_p = 100 - (((int(comp_len_kb)) / (Blk_Device_size*1024*1024)) * 100)
    # compression amount GB
    c_a = ( (100 - c_p) * Blk_Device_size ) / 100 
    output_dict['Compresion saving (%)'] = c_p
    output_dict['Compresion saving (GB)'] = c_a

    reduction = Blk_Device_size - int(((dedu_comp / 1024) / 1024) / 1024)
    reduction_perc = (reduction / Blk_Device_size) * 100
    output_dict['Total data reduction saving (%)'] = reduction_perc
    output_dict['Total data reduction saving (GB)'] = reduction
    output_json = json.dumps(output_dict)
    print(output_json)

def estimate_dedup(block_count, ram_limit, Blk_Device, unit_size):
    saved_block = 0
    for block_counter in range(0, block_count):
        if block_counter % 100000 == 0:
            ramsize = (sys.getsizeof(hash_table) / 1024) / 1024
            if int(ramsize) > ram_limit:
                print('ram used flushed')
                hash_table.clear()

        #read data from block device
        Blk_Device.seek(block_counter * unit_size)
        data = Blk_Device.read(unit_size)

        #check if data is duplicate
        if if_exist(data):
            saved_block += 1

        #if data is unique
        else:
            add_to_hash_table(data)

    duplicate_percentage = (saved_block / block_count) * 100
    saved_amount = (((saved_block * unit_size) / 1024) / 1024) / 1024
    output_dict = {
        'Deduplication saving (%)': duplicate_percentage,
        'Deduplication saving (GB)': saved_amount
    }
    output_json = json.dumps(output_dict)
    print(output_json)

# def for estimate compression
def estimate_compression(Blk_Device , Blk_Device_size , block_count , unit_size ):
    Blk_Device_size = int(Blk_Device_size)
    comp_len_KB = 0.0 
    for block_counter in range(0 , block_count ) :  
        # seek pointer to start point of blocks
        Blk_Device.seek(block_counter * unit_size )
        # read block
        chunk = Blk_Device.read(unit_size)
        # length of block 
        chunk_len = len(chunk)
        # length of block after compress
        comp_len = len(lz4.frame.compress(chunk))
        if ( comp_len > chunk_len ):
            comp_len = chunk_len
        comp_len_KB+= ( comp_len / 1024 )
        # limit float to two decimal
        comp_len_KB = round(comp_len_KB, 4)
        
        # compression percentage 
    C_P = 100 - ( ( int( comp_len_KB ) / (Blk_Device_size*1024*1024) ) * 100 )
    # compression amount GB
    C_A = ( (100 - C_P) * Blk_Device_size) / 100 
    output_dict = {'Compresion saving (%)' : C_P , 'Compresion saving (GB)' : C_A}
    output_json = json.dumps(output_dict)
    print(output_json)






#check if hash of data is duplicate in hashtable 
def if_exist(data):
    hash = mmh3.hash(data)
    if hash in hash_table.keys() : 
        return True
    else:
        return False


# add unique data hash to the hash table 
def add_to_hash_table(data):
    hash = mmh3.hash(data) 
    hash_table[hash]= '0'



if __name__ == "__main__":
    main()
    
