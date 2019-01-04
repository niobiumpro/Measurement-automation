import numpy as np
import numpy.linalg

from scipy.optimize import minimize
from scipy.optimize import differential_evolution
from scipy.optimize import fmin_l_bfgs_b

from scipy.signal import convolve2d

import matplotlib.pyplot as plt
from copy import deepcopy

"""
Tried to appliy fit to non-normalized Snapshot instance class snap1
Class tries to fit XY curve with parabola 
y(x, a,x0,y0) = a*(x-x0)^2 + y0
utilizing scipy.optimize methods
Only scipy.minimize method compatibility is implemented.
Designed to utilize all possible methods from scipy.optimize

Result: 
    Failed. Minimizing methods converge to the parameters area's borders,
    while varying all 3 parabola parameters.
    While only the extremum of parabola is varied (x0,y0) but not the y-scale, 
    mostly converges
    to the proper values.
    
Debug notes: 
    very useful to plot _loss_Q across the parameters values area
    as a 3D or color plots.
    
Usage example:
    see end of the file
"""

class TTS_fit:
    opt_funcs = {"minimize": minimize, "evolution": differential_evolution}

    def __init__(self,a_start,x0_start,y0_start,snapshot,
                 KERNEL_X_WIDTH=0.1, KERNEL_Y_WIDTH = 0.1, rel_threshold=0.4,
                 bounds=((-10, 10), (0.01, 0.99), (0.01, 0.99))):
        self.snapshot = deepcopy(snapshot)
        self.snap_normed = snapshot._normalize()
        self.snap_normed_abs = deepcopy(self.snap_normed)
        self.snap_normed_abs.data = np.abs(self.snap_normed.data)

        self.snap_thres = None
        self.snap_normed_thres = None
        self.set_new_rel_threshold(rel_threshold)

        self.a_start = a_start
        self.x0_start = x0_start
        self.y0_start = y0_start
        self.v0 = [self.a_start,self.x0_start,self.y0_start]

        self.KERNEL_X_WIDTH = KERNEL_X_WIDTH
        self.KERNEL_Y_WIDTH = KERNEL_Y_WIDTH

        self.bounds = bounds

        self._loss_Q_list = [self._loss_Q0]
        ## setting default minimization parameters ##
        self._loss_Q_idx = 0
        self._loss_Q = self._loss_Q_list[self._loss_Q_idx]

        self.var_flags = [1, 1, 1]
        self.var_bounds = self._generate_bounds()

        self.thres = False

        self.snap = self.snap_normed
        self.snap_data_abs = None

        self.scipy_func_name = "minimize"
        # scipy.optimize.minimize
        self.opt_func = TTS_fit.opt_funcs[self.scipy_func_name]
        self.opt_func_options = {}
        self.method = None

        ## result related attributes ##
        self.result = None

    def _get_v_from_x(self, x):
        v = []
        index = 0
        for i, flag in enumerate(self.var_flags):
            if flag == 1:
                v.append(x[index])
                index += 1
            else:
                v.append(self.v0[i])
        return v

    def _generate_bounds(self):
        bounds = []
        for i, flag in enumerate(self.var_flags):
            if flag == 1:
                bounds.append(self.bounds[i])
        return tuple(bounds)

    def setup(self, var_flags=[1,1,1], thres=None, scipy_func_name="minimize", method="SLSQP", opt_func_options={}, loss_Q_idx = 0):

        self.var_flags = var_flags
        self.var_bounds = self._generate_bounds()
        if thres is not None:
            self.set_new_rel_threshold(thres)
            self.snap = self.snap_normed_thres
        else:
            self.snap = self.snap_normed

        self.snap_data_abs = np.abs(self.snap.data)

        self.scipy_func_name = scipy_func_name
        self.opt_func = TTS_fit.opt_funcs[self.scipy_func_name]
        self.method = method
        self.opt_func_options = opt_func_options

        self._loss_Q_idx = loss_Q_idx
        self._loss_Q = self._loss_Q_list[loss_Q_idx]

    def set_new_rel_threshold(self,rel_threshold):
        self.snap_thres = self.snapshot._nullify_rel_threshold(rel_threshold)
        self.snap_normed_thres = self.snap_normed._nullify_rel_threshold(rel_threshold)

    def _y_x(self, x, a, x0, y0):
        y = a * (x - x0) ** 2 + y0
        return y

    def _y2idxs(self, y):
        y_idxs = np.array((y - self.snap_normed.y[0]) / self.snap_normed.dy - 1, dtype=np.intp)
        return y_idxs

    def _loss_Q_wrapper(self, x):
        v = np.array(self._get_v_from_x(x))
        return self._loss_Q(v)

    def _loss_Q0(self, x):
        ai = x[0]
        xi = x[1]
        yi = x[2]

        z_field = self._get_z_field(ai,xi,yi)

        return np.linalg.norm(z_field - self.snap_data_abs)

    def _get_z_field(self,ai,xi,yi):
        y_vals = self._y_x(self.snap.x, ai, xi, yi)
        y_idxs = self._y2idxs(y_vals)

        # y_idxs_inside_mask[i] contains index i of the x[i], where y(x[i]) lies in picture
        y_idxs_inside_mask = (y_idxs >= 0) & (y_idxs < len(self.snap.y))

        # forming 2 arrays of the same length that could be plotted with plt.scatter(x,y)
        # and their values lies inside the picture (all x values lies inside by default)
        # but only y_idxs[y_idxs_inside_mask] contains inside the picture
        # x_idxs[y_idxs_inside_mask] is their corresponding 'x' values
        x_idxs = np.array(range(0, len(self.snap.x)), dtype=np.intp)[y_idxs_inside_mask]
        y_idxs = y_idxs[y_idxs_inside_mask]

        # filling new picture with 1.0 at every x[x_idxs[i]],y[y_idxs[i]]
        z_field = np.full_like(self.snap.data, 0.0, dtype=np.float64)
        z_field[y_idxs, x_idxs] = 1.0

        # smoothing z_field data points
        kernel_x = int(round(self.KERNEL_X_WIDTH / self.snap.dx))
        kernel_y = int(round(self.KERNEL_Y_WIDTH / self.snap.dy))
        kernel = [[np.exp(-(i - kernel_x / 2) ** 2 * self.snap.dx - (j - kernel_y / 2) ** 2 * self.snap.dy) for i in
                   range(kernel_x)] for j in range(kernel_y)]

        kernel2 = convolve2d(kernel, kernel, mode="full", fillvalue=0.0)
        z_field = convolve2d(z_field, kernel2, mode="same", fillvalue=0.0)

        z_field /= np.amax(z_field)

        return z_field

    def fit(self, callback=None):
        if self.scipy_func_name == "minimize":
            ig = []
            x0 = (self.a_start, self.x0_start, self.y0_start)

            for i, flag in enumerate(self.var_flags):
                if flag == 1:
                    ig.append(x0[i])
            ig=np.array(ig)

            self.result = self.opt_func(self._loss_Q_wrapper, ig,
                                        method=self.method, bounds=self.var_bounds,
                                        callback=callback,
                                        **self.opt_func_options)
        return self.result

    def _print(self, x):
        print(x)

    def plot_fit(self):
        x = self.result.x
        v = self._get_v_from_x(x)
        a = v[0]
        x0 = v[1]
        y0 = v[2]

        z_field = self._get_z_field(a,x0,y0)

        data = np.abs(z_field - self.snap_data_abs)

        snap2plot = deepcopy(self.snap)
        snap2plot.data = data
        return snap2plot.plot()


"""
Call example from .ipynb file: 

x0 = 0.3
y0 = 0.9

fc = TTS_fit(-2,x0,y0,snap1)

SLSQP_options = {"eps":0.1,"ftol":1e-10, "disp":True}
fc.setup([0,1,1],method="TNC")

fc.fit(fc._print)

fc.plot_fit()
"""

"""
### EVALUATION OF LOSS_Q OVER THE (x0,y0) PARAMETERS AREA (0.0;1.0)x(0.0;1.0) ###
### NEEDS REPAIR TO EXECUTE

snap = deepcopy(snap1)
snap_normed = snap._normalize()#._nullify_rel_threshold(0.5)
nx = 100
ny = 100
x = np.linspace(0.01, 1.0, nx)
y = np.linspace(0.01, 1.0, ny)
z = np.zeros((nx,ny),dtype=np.float64)
snap_res = deepcopy(snap_normed)
snap_res.x = x
snap_res.y = y
snap._init_dependent_attributes()

snap_tmp = deepcopy(snap_normed)

a = -2
for i,xi in enumerate(x):
    for j,yi in enumerate(y):
#         print("x,y: ", xi, yi)
        y_vals = y_from_x(snap_normed.x, a, xi, yi)
        y_idxs = y2idxs(y_vals,snap_normed)
        
        # y_idxs_inside_mask[i] contains index i of the x[i], where y(x[i]) lies in picture
        y_idxs_inside_mask = (y_idxs >= 0) & (y_idxs < len(snap_normed.y))
#         print(y_idxs_inside_mask)
        
        # forming 2 arrays of the same length that could be plotted with plt.scatter(x,y)
        x_idxs = np.array(range(0,len(snap_normed.x)), dtype=np.intp)[y_idxs_inside_mask]
        y_idxs = y_idxs[y_idxs_inside_mask]
        
        # filling new picture with 1.0 at every x[x_idxs[i]],y[y_idxs[i]]
        z_field = np.full_like(snap_normed.data,0.0,dtype=np.float64)
        z_field[y_idxs, x_idxs] = 1.0

        KERNEL_X_WIDTH = 0.1
        KERNEL_Y_WIDTH = 0.1
        kernel_x = int(round(KERNEL_X_WIDTH/snap_normed.dx))
        kernel_y = int(round(KERNEL_Y_WIDTH/snap_normed.dy))
        kernel = [[np.exp(-(i-kernel_x/2)**2*snap_normed.dx-(j-kernel_y/2)**2*snap_normed.dy) for i in range(kernel_x)] for j in range(kernel_y)]

        kernel2 = convolve2d(kernel,kernel,mode="full",fillvalue=0.0)
#         print(kernel2.shape)
        z_field = convolve2d(z_field,kernel2,mode="same",fillvalue=0.0)
        z_field /= np.amax(z_field)
#         snap_tmp.data = z_field
#         snap_tmp.plot()
        
#         snap_tmp.data = z_field - np.abs(snap_normed.data)
#         snap_tmp.plot()
        
        res_loc = np.linalg.norm(z_field - np.abs(snap_normed.data))
        z[j,i] = res_loc
print("finished")

snap_res.data = z
#snap_res.data[snap_res.data > 1e4] = 0
snap_res._normalize().plot()



fig = plt.figure()
ax = fig.gca(projection='3d')

# Make data.
X, Y = np.meshgrid(x, y)
z = snap_res.data
# snap1_normed = snap1._normalize()
# X, Y = np.meshgrid(snap1_normed.x, snap1_normed.y)
# z = np.abs(snap1_normed.data)

surf = ax.plot_surface(X, Y, z, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)

ax.zaxis.set_major_locator(LinearLocator(10))
ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))
fig.colorbar(surf, shrink=0.5, aspect=5)

np.amin(z)
"""