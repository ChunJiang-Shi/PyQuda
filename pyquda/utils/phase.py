from typing import List

import numpy

from .. import getGridSize, getGridCoord, getCUDABackend


def isqrt(n):
    if n > 0:
        x = 1 << (n.bit_length() + 1 >> 1)
        while True:
            y = (x + n // x) >> 1
            if y >= x:
                return x
            x = y
    elif n == 0:
        return 0
    else:
        raise ValueError("Integer square root not defined for negative numbers.")


def getMomList(mom2_max, mom2_min=0):
    mom_list = []
    radius = isqrt(mom2_max)
    for npz in range(-radius, radius + 1):
        for npy in range(-radius, radius + 1):
            for npx in range(-radius, radius + 1):
                np2 = npx**2 + npy**2 + npz**2
                if np2 <= mom2_max and np2 >= mom2_min:
                    mom_list.append((npx, npy, npz))
    return mom_list


def getMomDict(mom2_max, mom2_min=0):
    mom_list = getMomList(mom2_max, mom2_min)
    mom_dict = {key: " ".join([str(np) for np in val]) for key, val in enumerate(mom_list)}
    return mom_dict


class Phase:
    def __init__(self, latt_size: List[int]) -> None:
        Lx, Ly, Lz, Lt = latt_size
        Gx, Gy, Gz, Gt = getGridSize()
        gx, gy, gz, gt = getGridCoord()
        x = numpy.arange(gx * Lx, (gx + 1) * Lx).reshape(1, 1, Lx).repeat(Lz, 0).repeat(Ly, 1) * (
            2j * numpy.pi / (Lx * Gx)
        )
        y = numpy.arange(gy * Ly, (gy + 1) * Ly).reshape(1, Ly, 1).repeat(Lz, 0).repeat(Lx, 2) * (
            2j * numpy.pi / (Ly * Gy)
        )
        z = numpy.arange(gz * Lz, (gz + 1) * Lz).reshape(Lz, 1, 1).repeat(Ly, 1).repeat(Lx, 2) * (
            2j * numpy.pi / (Lz * Gz)
        )
        x_cb2 = numpy.zeros((2, Lt, Lz, Ly, Lx // 2), "<c16")
        y_cb2 = numpy.zeros((2, Lt, Lz, Ly, Lx // 2), "<c16")
        z_cb2 = numpy.zeros((2, Lt, Lz, Ly, Lx // 2), "<c16")
        for it in range(Lt):
            for iz in range(Lz):
                for iy in range(Ly):
                    ieo = (it + iz + iy) % 2
                    if ieo == 0:
                        x_cb2[0, it, iz, iy] = x[iz, iy, 0::2]
                        x_cb2[1, it, iz, iy] = x[iz, iy, 1::2]
                        y_cb2[0, it, iz, iy] = y[iz, iy, 0::2]
                        y_cb2[1, it, iz, iy] = y[iz, iy, 1::2]
                        z_cb2[0, it, iz, iy] = z[iz, iy, 0::2]
                        z_cb2[1, it, iz, iy] = z[iz, iy, 1::2]
                    else:
                        x_cb2[1, it, iz, iy] = x[iz, iy, 0::2]
                        x_cb2[0, it, iz, iy] = x[iz, iy, 1::2]
                        y_cb2[1, it, iz, iy] = y[iz, iy, 0::2]
                        y_cb2[0, it, iz, iy] = y[iz, iy, 1::2]
                        z_cb2[1, it, iz, iy] = z[iz, iy, 0::2]
                        z_cb2[0, it, iz, iy] = z[iz, iy, 1::2]
        backend = getCUDABackend()
        if backend == "cupy":
            import cupy

            self.x = cupy.asarray(x_cb2)
            self.y = cupy.asarray(y_cb2)
            self.z = cupy.asarray(z_cb2)
        elif backend == "torch":
            import torch

            self.x = torch.as_tensor(x_cb2, device="cuda")
            self.y = torch.as_tensor(y_cb2, device="cuda")
            self.z = torch.as_tensor(z_cb2, device="cuda")

    def __getitem__(self, momentum: List[int]):
        npx, npy, npz = momentum
        backend = getCUDABackend()
        if backend == "cupy":
            import cupy

            return cupy.exp(npx * self.x + npy * self.y + npz * self.z)
        elif backend == "torch":
            import torch

            return torch.exp(npx * self.x + npy * self.y + npz * self.z)

    def cache(self, mom_list: List[List[int]]):
        backend = getCUDABackend()
        if backend == "cupy":
            import cupy

            ret = cupy.zeros((len(mom_list), *self.x.shape), "<c16")
        elif backend == "torch":
            import torch

            ret = torch.zeros((len(mom_list), *self.x.shape), dtype=backend.complex128, device="cuda")
        for idx, mom in enumerate(mom_list):
            ret[idx] = self.__getitem__(mom)
        return ret
