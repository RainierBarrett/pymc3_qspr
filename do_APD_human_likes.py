import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import sys
import math
import copy

def printhelp():
    print("Usage: do_APD_human_likes.py [human_gaussians_directory] [num_gauss_clusters] [ROC_distance_weight] [APD_data_directory]")
    exit(1)

if len(sys.argv) != 5:
    printhelp()

GAUSSDIR = sys.argv[1]
NUM_CLUSTERS = int(sys.argv[2])
PREFACTOR = float(sys.argv[3])
APD_DIR = sys.argv[4]
DATA_DIR = '/home/rainier/pymc3_qspr/data/'
APDFILE = DATA_DIR + 'APD_GPOS_SEQS.out'
APDTRAINFILE = APD_DIR+'/train_set.txt'
APDTESTFILE = APD_DIR+'/test_set.txt'
HUMANFILE = DATA_DIR + 'Human_all.out'
HUMAN_DATA = pd.read_csv(HUMANFILE)
APD_DATA = pd.read_csv(APDFILE)
FAKEFILE = DATA_DIR + 'shorter_pdb_distributed_peps.out'
FAKE_DATA = pd.read_csv(FAKEFILE)

ALPHABET = ['A','R','N','D','C','Q','E','G','H','I',
            'L','K','M','F','P','S','T','W','Y','V']

def get_hist_prob(bins, counts, value):
    '''takes in the bins and counts from a normalized numpy.histogram() and a value,
        returns the height of the bin that value falls into.'''
    idx = np.argmax(bins > value)
    if idx==0:
        return(0)
    else:
        return(counts[idx-1]/np.sum(counts))
    
def pep_to_int_list(pep):
    '''takes a single string of amino acids and translates to a list of ints'''
    return(list(map(ALPHABET.index, pep.replace('\n', ''))))

def read_data(trainfile, testfile):
    '''Takes a properly-formatted peptide datafile (each line MUST start with a sequence)
       and reads it into a list.'''
    train_data = {}#dict keyed by peptide length containing the sequences
    test_data = {}
    test_peptides = []
    train_peptides = []
    big_aa_string = ''#for training the whole background distro
    with open(trainfile, 'r') as f:
        lines = f.readlines()
        nlines = len(lines)
        start_idx = (1 if ('#' in lines[0] or 'sequence' in lines[0]) else 0)
        for line in lines[start_idx:]:#skip the header
            pep = line.split(',')[0]
            train_peptides.append(pep)
            length = len(pep)
            big_aa_string+=pep
            if(length not in train_data.keys()):
                train_data[length] = [(pep_to_int_list(pep))]
            else:
                train_data[length].append((pep_to_int_list(pep)))
    with open(testfile, 'r') as f:
        lines = f.readlines()
        nlines = len(lines)
        start_idx = (1 if ('#' in lines[0] or 'sequence' in lines[0]) else 0)
        for line in lines[start_idx:]:#skip the header
            pep = line.split(',')[0]
            test_peptides.append(pep)
            length = len(pep)
            big_aa_string+=pep
            if(length not in test_data.keys()):
                test_data[length] = [(pep_to_int_list(pep))]
            else:
                test_data[length].append((pep_to_int_list(pep)))
    big_aa_list = pep_to_int_list(big_aa_string)
    return(test_peptides, train_peptides, train_data, test_data, big_aa_list)

def calc_prob(peptide, bg_dist,  motif_dists):
    '''For use when we're OUTSIDE the model, for generating ROC data and the like.'''
    length = len(peptide)
    if(length - MOTIF_LENGTH +1 > 0 and MOTIF_LENGTH > 0):
        start_dist = np.ones(length - MOTIF_LENGTH +1) /(length-MOTIF_LENGTH+1)#uniform start dists
        prob = 0.0
        for i in range(length):
            for j in range(length - MOTIF_LENGTH+1):
                for k in range(NUM_MOTIF_CLASSES):
                    if(i < j or i >= j+MOTIF_LENGTH):#not in a motif 
                        prob += bg_dist[peptide[i]] * start_dist[j]
                    else:#we are in a motif 
                        prob += motif_dists[k][i-j][peptide[i]] * start_dist[j]
    else:#impossible to have a motif of this length, all b/g
        prob = 0.0
        for i in range(length):
            prob += bg_dist[peptide[i]]
    prob /= float(length)
    return(prob)

def calc_positives(arr, cutoff):
    '''takes in an array of probs given by the above model and returns the number of
       probs above the cutoff probability. This is for use in generating the ROC curve.'''
    arr = np.sort(np.array(arr))
    if not arr[-1] < cutoff:
        return(len(arr) - np.argmax(arr > cutoff))
    else:
        return(0)

def gen_roc_data(npoints, fpr_arr, tpr_arr, roc_min, roc_max, fakes,
                 trains, tests):
    '''This fills two numpy arrays for use in plotting the ROC curve. The first is the FPR,
       the second is the TPR. The number of points is npoints. Returns (FPR_arr, TPR_arr).'''
    best_cutoff = 0.0
    best_ROC = 0.0
    roc_range = np.linspace(roc_min, roc_max, npoints)
    #for each cutoff value, calculate the FPR and TPR
    for i in range(npoints):
        fakeset_positives = calc_positives(fakes, roc_range[i])
        fpr_arr[i] = float(fakeset_positives) / len(fakes)
        test_positives =  calc_positives(tests, roc_range[i])
        train_positives = calc_positives(trains, roc_range[i])
        tpr_arr[i] = float(train_positives + test_positives) / (len(trains) + len(tests) )
    best_idx = 0
    old_dist = 2.0
    for i in range(0,npoints):
        dist = math.sqrt(PREFACTOR * fpr_arr[i] **2 + (1-tpr_arr[i]) **2)
        if (old_dist > dist and fpr_arr[i] > 0):
            best_idx = i
            old_dist = dist
    best_cutoff = roc_range[best_idx]
    accuracy = (tpr_arr[best_idx] + (1.0-fpr_arr[best_idx]))/2.0
    return( ( accuracy, best_idx, best_cutoff))

    
#The Gibbs part

print("READING DATA...")
test_peps, train_peps, test_seqs, train_seqs, all_apd_aa = read_data(APDTRAINFILE, APDTESTFILE)


#the Gaussmix part
keys = ['netCharge', 'nChargedGroups', 'nNonPolarGroups']#the 3 key descriptors
counts = {}
bins = {}
for key in keys:
    counts[key] = np.genfromtxt('{}/{}_clusters_{}_observed.counts'.format(GAUSSDIR, NUM_CLUSTERS, key))
    bins[key] = np.genfromtxt('{}/{}_clusters_{}_observed.bins'.format(GAUSSDIR, NUM_CLUSTERS, key))


print("CALCULATING PROBABILITIES...")
#human data
human_gauss_probs = []
#APD data
apd_test_gauss_probs = []
apd_train_gauss_probs = []
fake_gauss_probs = []

for pep in test_peps:
    prob = 0.0
    for key in keys:
        prob += get_hist_prob(bins[key], counts[key], APD_DATA.loc[APD_DATA['sequence'] == pep][key].iloc[0])/3.0
    apd_test_gauss_probs.append(prob)

for pep in train_peps:
    prob = 0.0
    for key in keys:
        prob += get_hist_prob(bins[key], counts[key], APD_DATA.loc[APD_DATA['sequence'] == pep][key].iloc[0])/3.0
    apd_train_gauss_probs.append(prob)

for pep in HUMAN_DATA['sequence']:
    prob = 0.0
    for key in keys:
        prob += get_hist_prob(bins[key], counts[key], HUMAN_DATA.loc[HUMAN_DATA['sequence'] == pep][key].iloc[0])/3.0
    human_gauss_probs.append(prob)

for pep in FAKE_DATA['sequence']:
    prob = 0.0
    for key in keys:
        prob += get_hist_prob(bins[key], counts[key], FAKE_DATA.loc[FAKE_DATA['sequence'] == pep][key].iloc[0])/3.0
    fake_gauss_probs.append(prob)

'''Now that we have the probs given to the human data by the model, we get the best cutoff for the human data and see if any of the APD score above it.'''

NPOINTS = 5000
fpr_arr = np.zeros(NPOINTS)
tpr_arr = np.zeros(NPOINTS)
roc_min = min(min(fake_gauss_probs), min(human_gauss_probs))
roc_max = max(max(fake_gauss_probs), max(human_gauss_probs))

accuracy, best_idx, cutoff = gen_roc_data(NPOINTS, fpr_arr, tpr_arr, roc_min, roc_max, fake_gauss_probs, human_gauss_probs, [0.0])

num_human_like_apd = 0
human_like_train_indices = []
human_like_test_indices = []

for i in range(len(apd_test_gauss_probs)):
    if(apd_test_gauss_probs[i] - cutoff > 0.0):
        num_human_like_apd += 1
        human_like_test_indices.append(i)

        
for i in range(len(apd_train_gauss_probs)):
    if(apd_train_gauss_probs[i] - cutoff > 0.0):
        num_human_like_apd += 1
        human_like_train_indices.append(i)
    
best_test_idx = np.argmax(apd_test_gauss_probs)
best_train_dix = np.argmax(apd_train_gauss_probs)

print("Best candidates: {} and {}".format(train_peps[best_train_dix], test_peps[best_test_idx]))
