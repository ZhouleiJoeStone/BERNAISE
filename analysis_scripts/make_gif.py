""" make_gif script """
from common import info, info_cyan
from postprocess import get_steps, rank, size, comm
import os
from utilities.plot import plot_fancy
import numpy as np


def description(ts, **kwargs):
    info("Make a fancy gif animation.")


def method(ts, show=False, save=True, dt=None, fps=25, skip=0,
           delete_after=True, plot_u=False, inverse_phase=False, **kwargs):
    """ Make fancy gif animation. """
    info_cyan("Making a fancy gif animation.")
    anim_name = "animation"
    ts.compute_charge()

    steps = get_steps(ts, dt)[::(skip+1)]

    for step in steps[rank::size]:
        info("Step " + str(step) + " of " + str(len(ts)))
        if "phi" in ts:
            phi = ts["phi", step][:, 0]
        else:
            phi = np.zeros(len(ts.nodes))-1.
        if inverse_phase:
            phi = -phi
        charge = ts["charge", step][:, 0]
        charge_max = max(ts.max("charge"), -ts.min("charge"))
        charge_max = max(charge_max, 1e-8)  # Remove numerical noise
        if plot_u and "u" in ts:
            u = ts["u", step]
        else:
            u = None

        if save:
            save_file = os.path.join(ts.tmp_folder,
                                     anim_name + "_{:06d}.png".format(step))
        else:
            save_file = None

        plot_fancy(ts.nodes, ts.elems, phi, charge,
                   charge_max=charge_max, show=show, u=u,
                   save=save_file)

    comm.Barrier()
    if save and rank == 0:
        tmp_files = os.path.join(ts.tmp_folder, anim_name + "_*.png")
        anim_file = os.path.join(ts.plots_folder, anim_name + ".gif")

        os.system(("convert -delay {delay} {tmp_files} -trim +repage"
                   " -loop 0 {anim_file}").
                  format(tmp_files=tmp_files,
                         anim_file=anim_file, delay=int(100./fps)))
        if delete_after:
            os.system("rm {tmp_files}".format(tmp_files=tmp_files))
