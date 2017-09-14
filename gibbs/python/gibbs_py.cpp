#include "gibbs_py.h"
#include <string>
#include <boost/foreach.hpp>

namespace bpy = boost::python;
using namespace Gibbs;

char const * Gibbs_Py::test_print(){
  //a whole bunch of test cases. this is ad-hoc and bad
  /*if(_num_iters == 3000){
    return("NRUNS INITIALIZATION WORKS");
  }
  else{
    return("NRUNS INITIALIZATION FAILED");
    }*/
/*  if(_peptides.has_key(5)){
    if(bpy::len(_peptides[5][0]) == 5){
      return("CORRECT LENGTH");
    }
    else{
      return("INCORRECT LENGTH");
    }
  }
  else{
    return("KEY NOT RECOGNIZED");
    }*/
/*  if(_peptides[5][39][4] == 11){
    return("CORRECT LAST LAST ENTRY");
  }
  else{
    return("INCORRECT LAST LAST ENTRY");
    }
  double test_val = get_tot_prob(_peptides[5][0], 5, _bg_dist, _motif_dists, _motif_class_dists_map[5][0], _motif_start_dists_map[5][0], 0, 0);
  if(test_val < 0.000001){
    return("SUCCESS");
  }
  else{
    return("FAILURE");
    }
  double test_val = _motif_start_dists_map[5][0][0];
  if(test_val - 0.5 < 0.0000001 and test_val > 0.0){
    return("CORRECTLY PASSED MOTIF_START_DISTS");
  }
  else{
    return("INCORRECTLY PASSED MOTIF_START_DISTS");
    }
  double test_val = _motif_dists[0][0][0];
  if(test_val - 0.5 < 0.0000001 and test_val > 0.0){
    return("CORRECTLY PASSED MOTIF_DISTS");
  }
  else{
    return("INCORRECTLY PASSED MOTIF_DISTS");
    }*/
  return("This is a test.");
}

char const* Gibbs_Py::test_get_tot_prob(double test_prob, int idx){
//  double other_test_prob = bpy::extract<double>(test_prob);
  double local_test_prob = get_tot_prob(_peptides[5][idx], 5, _bg_dist, _motif_dists, _motif_class_dists_map[5][idx], _motif_start_dists_map[5][idx], -1, -1);
  if(abs(local_test_prob - test_prob) < EPSILON){
    return("TEST PASSED");
  }
  else{
    return("TEST FAILED");
  }
}

char const* Gibbs_Py::test_rng(double test_random){
  boost::uniform_01<boost::mt19937> zero_one(_rng);
  double local_random = zero_one();
  if(abs(local_random - test_random) < EPSILON){
    return("TEST PASSED");
  }
  else{
    return("TEST FAILED");
  }
}

void Gibbs_Py::do_bg_counts(int* peptide, int length, int start){
  for(int i = 0; i < length; i++){
    if (i < start or i >= (_motif_length + start) ){
      _local_bg_counts[peptide[i]]++;
    }
  }
}

void Gibbs_Py::get_possible_starts(std::vector<int> & starts, int key){
  starts.clear();
  for(int i = 0; i < (key - _motif_length + 1); i++){
    starts.push_back(i);
  }
  return;
}

int Gibbs_Py::random_choice(int num_choices, double* weights){
  //expects that the weights are normalized
  boost::uniform_01<boost::mt19937> zero_one(_rng);
  double rando = zero_one();
  for(int i = 0; i < num_choices; i++){
    if(rando < weights[i]){
      return(i);
    }
    rando -= weights[i];
  }
  return(-1);//will raise an error if we don't do it right.
}

void Gibbs_Py::update_bg_dist(){
  int bg_count_sum = 0;
  for (int i = 0; i < ALPHABET_LENGTH; i++){
    bg_count_sum += _local_bg_counts[i];
  }
  for (int i = 0; i < ALPHABET_LENGTH; i++){
    _bg_dist[i] = double(_local_bg_counts[i])/double(bg_count_sum);
  }
  return;
}

void Gibbs_Py::run(){
  /*
   * The main loop is embodied here. After calling run(), we must then pass all
   * the altered distros back to the python side of things with convert()
   */
  int i_key, key, i, j, k, step, poss_starts, motif_start, motif_class;
  int* pep;
  std::vector<int> possible_starts;
  for(step = 0; step < _num_iters; step++){
    //loop over keys
    for (i_key = 0; i_key < bpy::len(_keys); i_key++){
      key = bpy::extract<int>(_keys[i_key]);
      //loop over all peptides of that length
      for(i = 0; i < bpy::len(_peptides_dict[key]); i++){
	pep = _peptides[key][i];
	poss_starts = (key - _motif_length);
//	get_possible_starts(possible_starts, key);
	//randomly choose motif start
	motif_start = random_choice(poss_starts, _motif_start_dists_map[key][i]);
	do_bg_counts(pep, key, motif_start);
	update_bg_dist();
	motif_class = random_choice(_num_motif_classes, _motif_class_dists_map[key][i]);
	for (j = 0; j < _motif_length; j++){
	  _motif_counts[key][motif_class][j][pep[j+motif_start]] += 1;
	}
      }
    }
  }
  return;
}

double Gibbs_Py::Gibbs_Py::get_tot_prob(int* peptide,
					int length,
					double* bg_dist,
					double*** motif_dists,//3D arr
					double* class_dist,//specific distro we're using here
					double* start_dist,
					int motif_class,
					int motif_start){
  //these are all internal variables that will be used; don't call this from python.
  /*
   * Takes in a peptide as an int array, the lenght of that peptide,
   * a double arr containing the background distro, a 3D arr of doubles containing
   * the motif distros, a double arr containing the class distro, a double arr 
   * containing the motif start distro, the current motif class (if applicable, else -1),
   * and the current motif start position (if applicable, else -1). Returns the 'total'
   * un-normalized probability density assigned to this peptide with these params.
   */
  double prob = 0.0;
  int i, j, k;
  if((motif_start >= 0) and motif_start < (length - _motif_length)){//use set value for motif_start
    if((motif_class >=0) and (motif_class < _num_motif_classes)){//use set value for motif_class
      for (i = 0; i < length; i++){
	for (j = 0; j < (length - _motif_length + 1); j++){
	  for (k = 0; k < _num_motif_classes; k++){
	    if( i < motif_start or i >= (motif_start + _motif_length)){
	      prob += bg_dist[peptide[i]] * start_dist[j] * class_dist[motif_class];
	    }
	    else{
	      prob += motif_dists[motif_class][ i - motif_start][peptide[i]] * start_dist[j] * class_dist[motif_class];
	    }
	  }
	}
      }
    }
    else{//
      for (i = 0; i < length; i++){
	for (j = 0; j < (length - _motif_length + 1); j++){
	  for (k = 0; k < _num_motif_classes; k++){
	    if( i < motif_start or i >= (motif_start + _motif_length)){//not in a motif
	      prob += bg_dist[peptide[i]] * start_dist[j] * class_dist[k];
	    }
	    else{//in a motif
	      prob += motif_dists[k][i - motif_start][peptide[i]] * start_dist[j] * class_dist[k];
	    }
	  }
	}
      }
    }
  }
  else{//use start_dist; no set value
    if ((motif_class >=0) and (motif_class < _num_motif_classes)){//use set value for motif_class
      for (i = 0; i < length; i++){
	for (j = 0; j < (length - _motif_length + 1); j++){
	  for (k = 0; k < _num_motif_classes; k++){
	    if( i < j or i >= (j + _motif_length)){//not in a motif
	      prob += bg_dist[peptide[i]] * start_dist[j] * class_dist[k];
	    }
	    else{//in a motif
	      prob += motif_dists[motif_class][i - j][peptide[i]] * start_dist[j] * class_dist[k];
	    }
	  }
	}
      }
    }
    else{
      for (i = 0; i < length; i++){
	for (j = 0; j < (length - _motif_length + 1); j++){
	  for (k = 0; k < _num_motif_classes; k++){
	    if( i < j or i >= (j + _motif_length)){//not in a motif
	      prob += bg_dist[peptide[i]] * start_dist[j] * class_dist[k];
	    }
	    else{//in a motif
	      prob += motif_dists[k][i - j][peptide[i]] * start_dist[j] * class_dist[k];
	    }
	  }
	}
      }
    }
  }
  
  return(prob);
}

Gibbs_Py::Gibbs_Py(bpy::dict training_peptides,
		   bpy::dict motif_counts,
		   bpy::dict motif_start_dists,
		   bpy::dict motif_class_dists,
		   bpy::list bg_counts,
		   bpy::list tot_bg_counts,
		   int num_iters,
		   int motif_length,
  		   int num_motif_classes,
		   int rng_seed){
  _motif_counts = motif_counts;
  _peptides_dict = training_peptides;
  _motif_start_dists = motif_start_dists;
  _motif_class_dists = motif_class_dists;
  _bg_counts = bg_counts;
  _tot_bg_counts = tot_bg_counts;
  _num_iters = num_iters;
  _motif_length = motif_length;
  _num_motif_classes = num_motif_classes;
  _local_bg_counts = new int[ALPHABET_LENGTH];
  _bg_dist = new double[ALPHABET_LENGTH];//the length of the alphabet
  _motif_dists = new double**[_num_motif_classes];

  _keys = training_peptides.keys();
  int key, length, i, j, k;

  _rng = boost::random::mt19937(rng_seed);

  

  for(i = 0; i < ALPHABET_LENGTH; i++){
    _local_bg_counts[i] = 0;
    _bg_dist[i] = 1.0/float(ALPHABET_LENGTH);
  }

  for (i = 0; i < bpy::len(training_peptides.keys()); i++){
    key = bpy::extract<int>(_keys[i]);
    length = bpy::len(training_peptides[key]);
    _peptides[key] = new int*[length];
    for(j = 0; j < length; j++){
      _peptides[key][j] = new int[key];//keyed by length
      for(k = 0; k < key; k++){
	_peptides[key][j][k] = bpy::extract<int>(training_peptides[key][j][k]);
      }
    }
  }

  for (i = 0; i < _num_motif_classes; i++){
    _motif_dists[i] = new double*[_motif_length];
  }
  for ( i = 0; i < _num_motif_classes; i++){
    for( j = 0; j < _motif_length; j++){
      _motif_dists[i][j] = new double[ALPHABET_LENGTH];
    }
  }

  for( i = 0; i < bpy::len(training_peptides.keys()); i++){
    key = (bpy::extract<int>(_keys[i]));
    length = bpy::len(training_peptides[key]);
    _motif_start_dists_map[key] = new double*[length];
    _motif_class_dists_map[key] = new double*[length];
    _motif_counts_map[key] = new int**[_num_motif_classes];
    for( j = 0; j < length; j++){
      _motif_start_dists_map[key][j] = new double[key - _motif_length +1];
      _motif_class_dists_map[key][j] = new double[_num_motif_classes];
      if(j < num_motif_classes){
	_motif_counts_map[key][j] = new int*[_motif_length];
	for(k = 0; k < _num_motif_classes; k++){
	  _motif_counts_map[key][j][k] = new int[ALPHABET_LENGTH];
	}
      }
      for( k = 0; k < key - _motif_length +1; k++){
	_motif_start_dists_map[key][j][k] = bpy::extract<double>(motif_start_dists[key][j][k]);
      }
      for(k = 0; k < _num_motif_classes; k++){
	_motif_class_dists_map[key][j][k] = bpy::extract<double>(motif_class_dists[key][j][k]);
      }
    }
  }
  //AT THE END OF THE LOOP, REPLACE DICT CONTENTS WITH THE UPDATED DISTROS

  
};

Gibbs_Py::~Gibbs_Py(){
  if(_bg_dist){
    delete [] _bg_dist;
  }
  if(_motif_dists){
    delete [] _motif_dists;    
  }

  int key, length, i, j, k;

  for( i = 0; i < bpy::len(_keys); i++){
    key = bpy::extract<int>(_keys[i]);
    length = sizeof(_peptides[key])/sizeof(int*);
    for( j = 0; j < length; j++){
	delete [] _motif_start_dists_map[key][j];
	delete [] _motif_class_dists_map[key][j];
    }
    for(j = 0; j < _num_motif_classes; j++){
      delete [] _motif_counts_map[key][j];
    }
  }
}
