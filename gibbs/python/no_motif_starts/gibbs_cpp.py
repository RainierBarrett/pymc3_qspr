import numpy as np
import re
import math
import matplotlib as mpl
from matplotlib import pyplot as plt
import pdb
import sys
import os
import libgibbs as lg
import random
import time
import sys
from qspr_plots import *



def printhelp():
    print("Usage: test_gibbs.py [test_peptides_file] [num_classes] [num_iterations] [alpha] [random_draws_per_step (default 0)]")
    exit(1)

if len(sys.argv) != 5 and len(sys.argv) != 6:
    printhelp()

INPUT = sys.argv[1]
NUM_MOTIF_CLASSES = int(sys.argv[2]) #one class for which letter the motif starts with? why not try
NRUNS = int(sys.argv[3])
ALPHA = float(sys.argv[4])
if(len(sys.argv) == 6):
    NUM_RANDOM_DRAWS = int(sys.argv[5])
else:
    NUM_RANDOM_DRAWS = 0


#CONSTANTS
MOTIF_LENGTH = 4 #fixed motif lengths, for now
HOMEDIR = '.'

DATA_DIR = '/home/rainier/pymc3_qspr/data/'
fakefile = DATA_DIR + 'pdb_distributed_apd_length_peps.txt'

def read_data(datafile):
    '''Takes a properly-formatted peptide datafile (each line MUST start with a sequence)
       and reads it into a list.'''
    data = {}#dict keyed by peptide length containing the sequences
    with open(datafile, 'r') as f:
        big_aa_string = ''#for training the whole background distro
        lines = f.readlines()
        nlines = len(lines)
        start_idx = (1 if ('#' in lines[0] or 'sequence' in lines[0]) else 0)
        for line in lines[start_idx:]:#skip the header
            pep = line.split(',')[0]
            length = len(pep)
            big_aa_string+=pep
            if(length not in data.keys()):
                data[length] = [(pep_to_int_list(pep))]
            else:
                data[length].append((pep_to_int_list(pep)))
        big_aa_list = pep_to_int_list(big_aa_string)
    return(data, big_aa_list)


apd_data, all_apd_aa  = read_data(INPUT)#('/home/rainier/pymc3_qspr/gibbs/control_peptides.txt')

#initialize the OVERALL distributions as uniform
motif_dists = np.ones((NUM_MOTIF_CLASSES, MOTIF_LENGTH, len(ALPHABET))) / float(len(ALPHABET))

tot_motif_counts = {}#keep track of raw counts for EACH peptide separately
for key in apd_data.keys():
    tot_motif_counts[key] = np.zeros((NUM_MOTIF_CLASSES, MOTIF_LENGTH, len(ALPHABET)))

motif_counts = {}#this one is for local counting within the loop only.
for key in apd_data.keys():
    motif_counts[key] = np.zeros((NUM_MOTIF_CLASSES, MOTIF_LENGTH, len(ALPHABET)))


bg_dist = np.ones(len(ALPHABET))/float(len(ALPHABET))
#distributions not tracked by peptide, just length.
motif_start_dists = {}
motif_class_dists = {}
#raw counts tracked PER peptide
motif_start_counts = {}
#motif_class_counts = {}
for key in apd_data.keys():
    motif_start_dists[key] = np.ones((len(apd_data[key]), (key - MOTIF_LENGTH+1)))/float(key - MOTIF_LENGTH+1)
    motif_start_counts[key] = np.zeros((len(apd_data[key]), (key - MOTIF_LENGTH +1)), dtype = int)
    motif_class_dists[key] = np.ones((len(apd_data[key]) , NUM_MOTIF_CLASSES)) / float(NUM_MOTIF_CLASSES)
#    motif_class_counts[key] = np.zeros((len(apd_data[key]) ,NUM_MOTIF_CLASSES))
bg_counts = np.zeros(len(ALPHABET), dtype=int)#times we see each AA as a b/g element
tot_bg_counts = np.zeros(len(ALPHABET), dtype=int)#times we see each AA as a b/g element

bg_count_list = bg_counts.tolist()
tot_bg_count_list = tot_bg_counts.tolist()
motif_dists_list = motif_dists.tolist()

RNG_SEED =  int(time.time())#98587106

sampler = lg.Gibbs_Py(apd_data,
                      motif_counts,
                      motif_start_dists,
                      motif_class_dists,
                      motif_dists_list,
                      bg_count_list,
                      tot_bg_count_list,
                      NRUNS,
                      MOTIF_LENGTH,
                      NUM_MOTIF_CLASSES,
                      RNG_SEED,
                      NUM_RANDOM_DRAWS,
                      ALPHA)

print("BEGINNING GIBBS SAMPLING...")
new_motif_dists, new_bg_dist, new_motif_start_dists, new_motif_class_dists = sampler.run()
print("GIBBS SAMPLING COMPLETE")


print("DRAWING PLOTS...")

outpath = '{}/gpos_{}_classes_length_{}'.format(HOMEDIR, NUM_MOTIF_CLASSES, MOTIF_LENGTH)
if not(os.path.exists(outpath)):
    os.makedirs(outpath)

for i in range(NUM_MOTIF_CLASSES):
    for j in range(MOTIF_LENGTH):
        fig = plt.figure()
        plt.xlabel('Amino Acid')
        plt.ylabel('Relative Frequency')
        plt.title('position {} in motif class {}'.format(j,i))
        plt.bar(range(len(ALPHABET)), new_motif_dists[i][j])
        plt.xticks(range(len(ALPHABET)), ALPHABET)
        plt.savefig('{}/class_{}_of_{}_position_{}_motif_dist.png'.format(outpath, i, NUM_MOTIF_CLASSES,j))
        plt.close(fig)
        np.savetxt('{}/class_{}_of_{}_position_{}_motif_dist.txt'.format(outpath, i, NUM_MOTIF_CLASSES, j), new_motif_dists[i][j])

fig = plt.figure()
plt.xlabel('Amino Acid')
plt.ylabel('Relative Frequency')
plt.title('Background Distribution')
plt.bar(range(len(ALPHABET)), new_bg_dist)
plt.xticks(range(len(ALPHABET)), ALPHABET)
plt.savefig('{}/bg_dist.png'.format(outpath))
plt.close(fig)
np.savetxt('{}/bg_dist.txt'.format(outpath), new_bg_dist)


collapsed_start_dists = {}
collapsed_class_dists = {}
for key in apd_data.keys():
    collapsed_start_dists[key] = np.sum(motif_start_dists[key], axis=0) / np.sum(motif_start_dists[key])
    collapsed_class_dists[key] = np.sum(motif_class_dists[key], axis=0) / np.sum(motif_class_dists[key])

for key in apd_data.keys():
    '''fig = plt.figure()
    plt.xlabel('Start Position')
    plt.ylabel('Relative Frequency')
    plt.title('Motif Length {} Start Position Histogram for Length {}'.format(MOTIF_LENGTH, key))
    plt.bar(range(key-MOTIF_LENGTH+1), collapsed_start_dists[key])
    plt.savefig('{}/motif_length_{}_length_{}_start_dist.png'.format(outpath, MOTIF_LENGTH, key))
    plt.close(fig)'''
    np.savetxt('{}/motif_length_{}_length_{}_start_dist.txt'.format(outpath, MOTIF_LENGTH, key), collapsed_start_dists[key])

for key in apd_data.keys():
    for i in range(len(apd_data[key])):
        '''fig = plt.figure()
        plt.xlabel('Motif Class')
        plt.ylabel('Relative Probability')
        plt.title('Motif Length {} Motif Class Histogram for Length {} Index {}'.format(MOTIF_LENGTH, key, i))
        plt.bar(range(NUM_MOTIF_CLASSES), motif_class_dists[key][i])
        plt.savefig('{}/motif_length_{}_length_{}_index_{}_class_dist.png'.format(outpath, MOTIF_LENGTH, key, i))
        plt.close(fig)'''
        np.savetxt('{}/motif_length_{}_length_{}_index_{}_class_dist.txt'.format(outpath, MOTIF_LENGTH, key, i), motif_class_dists[key][i])

with open('{}/info.txt'.format(outpath), 'w+') as f:
    f.write('NUM_CLASSES {}\n'.format(NUM_MOTIF_CLASSES))
    f.write('NRUNS {}\n'.format(NRUNS))
    f.write('ALPHA {}\n'.format(ALPHA))
    f.write('NOISE {}\n'.format(NUM_RANDOM_DRAWS))
    
