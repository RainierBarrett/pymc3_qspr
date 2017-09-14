#include <boost/python.hpp>
#include "gibbs_py.h"
using namespace Gibbs;
using namespace boost::python;


BOOST_PYTHON_MODULE(libgibbs)
{//, boost::python::object, boost::python::object, boost::python::object,  boost::python::list, boost::python::list, int>())
  class_<Gibbs_Py, boost::noncopyable>("Gibbs_Py", init<dict, dict, dict, dict, list, list, int, int, int, int>())
    .def("test_print", &Gibbs_Py::test_print)
    .def("run", &Gibbs_Py::run)
    .def("test_get_tot_prob", &Gibbs_Py::test_get_tot_prob)
    .def("test_rng", &Gibbs_Py::test_rng)
    ;
}
