import os
from dolfin import MPI, mpi_comm_world, XDMFFile, HDF5File
from cmd import info_red, info_cyan
import cPickle

__author__ = "Gaute Linga"
__date__ = "2017-05-26"
__copyright__ = "Copyright (C) 2017 " + __author__
__license__ = "MIT"

__all__ = ["create_initial_folders"]


def mpi_is_root():
    """ Check if current MPI node is root node. """
    return MPI.rank(mpi_comm_world()) == 0


def makedirs_safe(folder):
    """ Make directory in a safe way. """
    if mpi_is_root():
        if not os.path.exists(folder):
            os.makedirs(folder)


def dump_parameters(parameters, settingsfilename):
    """ Dump parameters to file """
    with file(settingsfilename, "w") as settingsfile:
        cPickle.dump(parameters, settingsfile)

            
def create_initial_folders(folder, restart_folder, fields, tstep,
                           parameters):
    """ Create initial folders """
    info_cyan("Creating folders.")

    makedirs_safe(folder)
    MPI.barrier(mpi_comm_world())
    if restart_folder:
        newfolder = os.path.join(folder, restart_folder.split("/")[-2])
    else:
        previous_list = os.listdir(folder)
        if len(previous_list) == 0:
            newfolder = os.path.join(folder, "1")
        else:
            previous = max([int(entry) if entry.isdigit() else 0
                            for entry in previous_list])
            newfolder = os.path.join(folder, str(previous+1))

    MPI.barrier(mpi_comm_world())
    tstepfolder = os.path.join(newfolder, "Timeseries")
    makedirs_safe(tstepfolder)
    makedirs_safe(os.path.join(newfolder, "Statistics"))
    settingsfolder = os.path.join(newfolder, "Settings")
    makedirs_safe(settingsfolder)
    makedirs_safe(os.path.join(newfolder, "Checkpoint"))

    # Initialize timestep files
    tstepfiles = dict()
    for field in fields:
        tstepfiles[field] = XDMFFile(
            mpi_comm_world(),
            os.path.join(tstepfolder,
                         field + "_from_tstep_{}.xdmf".format(tstep)))
        tstepfiles[field].parameters["rewrite_function_mesh"] = False
        tstepfiles[field].parameters["flush_output"] = True

    # Dump settings
    if mpi_is_root():
        dump_parameters(parameters, os.path.join(
            settingsfolder, "parameters_from_tstep_{}.dat".format(tstep)))

    return newfolder, tstepfiles


def save_solution(tstep, w_, w_1, folder, newfolder,
                  save_intv, checkpoint_intv,
                  parameters, tstepfiles):
    """ Save solution either to  """
    if tstep % save_intv == 0:
        # Save snapshot to xdmf
        save_xdmf(tstep, w_, tstepfiles)

    kill = check_if_kill(folder)
    if tstep % checkpoint_intv or kill:
        # Save checkpoint
        save_checkpoint(tstep, w_, w_1, newfolder, parameters)

    return kill


def check_if_kill(folder):
    """ Check if the user has order to kill the simulation """
    found = 0
    if "kill" in os.listdir(folder):
        found = 1
    found_all = MPI.sum(mpi_comm_world(), found)
    if found_all > 0:
        if MPI.rank(mpi_comm_world()) == 0:
            os.remove(os.path.join(folder, "kill"))
        info_red("Stopping simulation.")
        return True
    else:
        return False


def save_xdmf(tstep, w_, tstepfiles):
    """ Save snapshot of solution to xdmf file. """
    for field, tstepfile in tstepfiles:
        if field in w_:
            tstepfile.write(w_[field], float(tstep))


def save_checkpoint(tstep, w_, w_1, newfolder, parameters):
    """ Save checkpoint files.

    A part of this is taken from the Oasis code."""
    checkpointfolder = os.path.join(newfolder, "Checkpoint")
    parameters["num_processes"] = MPI.size(mpi_comm_world())
    if mpi_is_root():
        parametersfile = os.path.join(checkpointfolder, "parameters.dat")
        parametersfile_old = parametersfile + ".old"
        # In case of failure, keep old file.
        if os.path.exists(parametersfile):
            os.system("mv {0} {1}".format(parametersfile,
                                          parametersfile_old))
        dump_parameters(parameters, parametersfile)

    MPI.barrier(mpi_comm_world())
    h5filename = os.path.join(checkpointfolder, "fields.h5")
    h5filename_old = h5filename + ".old"
    h5file = HDF5File(mpi_comm_world(), h5filename, "w")
    h5file.flush()  # What does this do?
    for field in w_:
        # In case of failure, keep old file.
        if mpi_is_root() and os.path.exists(h5filename):
            os.system("mv {0} {1}".format(h5filename, h5filename_old))
        MPI.barrier(mpi_comm_world())
        h5file.write(w_[field], field + "/current")
        if field in w_1:
            h5file.write(w_1[field], field + "/previous")
        # Since program is still running, delete the old files.
        MPI.barrier(mpi_comm_world())
        if mpi_is_root() and os.path.exists(h5filename_old):
            os.system("rm {}".format(h5filename_old))
        MPI.barrier(mpi_comm_world())
    h5file.close()

    if mpi_is_root() and os.path.exists(parametersfile_old):
        os.system("rm {}".format(parametersfile_old))


def load_checkpoint(checkpointfolder, fields, w_, w_1):
    if checkpointfolder:
        h5filename = os.path.join(checkpointfolder, "fields.h5")
        h5file = HDF5File(mpi_comm_world(), h5filename, "r")
        for field in w_:
            h5file.read(w_[field], field + "/current", False)
            h5file.read(w_1[field], field + "/previous", False)
        h5file.close()