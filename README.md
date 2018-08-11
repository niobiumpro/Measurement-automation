# Measurement automation

This is the system designed to perform various experiments with superconducting quantum circuits. It was developed in response to the increasing number and diversity of tasks and provides a common framework for all of them.

It is fully open-source and is based on pyvisa, matplotlib, scipy, ipython (jupyter) and some other open-source packages (i.e. [resonator tools](https://github.com/sebastianprobst/resonator_tools) by S. Probst)

Features:
- Percievable and scalable object-oriented code (with encapsulation, polymorphism and inheritance)
- Distinct self-sufficient classes for each of the primitive experiments and their results with common interface
- Eye-pleasing visualization using matplotlib
- Real-time plotting and data collection in separate threads
- Image fitting modules to extract parameters of flux-tunable qubits from single-tone and two-tone heatmap spectra
- Real-time robust simultaneous real-imag curve fitting in time-resolved experiments
- Human-friendly storage and loading of raw data and measurement result objects (with pickle, high-res .png and .pdf plots)
- No GUI <img src=https://user-images.githubusercontent.com/3819012/42594391-bddafb04-8557-11e8-8565-1504d9e0f3de.png width=20>


The key goal of this project is to develop measurement protocols and fully automate processes to reduce overall human participation in experiments

## Gallery

Here some of the dispersive measurement results are presented

### Single-tone spectroscopy

![8-9ghz-random-anticrossings-shifted-w-coil](https://user-images.githubusercontent.com/3819012/42591823-8051e542-8550-11e8-8c11-3b7f65febb09.png)

 <p align="center"><i>Various anticrossings in a multimode sample</i></p>



### Two-tone spectroscopy

![default](https://user-images.githubusercontent.com/3819012/42592612-b2cc0ec4-8552-11e8-9031-dd6f66b5dfcf.png)
 <p align="center"><i>Two coupled transmons</i></p>

### Time-resolved experiments
<p align="center">
<img src=https://user-images.githubusercontent.com/3819012/42593084-20bb8c38-8554-11e8-8153-50706e86065d.png width=400><img src=https://user-images.githubusercontent.com/3819012/42593239-8ee7aaac-8554-11e8-9e5c-2a74fb548a43.png width=400></p>
 <p align="center"><i>Relaxation and dephasing</i></p>


![tomo_arb_state pdf](https://user-images.githubusercontent.com/3819012/42593726-ebdb4074-8555-11e8-86bf-956dfb715197.png)
 <p align="center"><i>Quantum state tomography (experiment and LSQ fit) for the preparation sequence +Y/4, +X/3</i></p>

