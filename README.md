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
- No GUI

The key goal of this project is to develop measurement protocols and fully automate processes to reduce overall human participation in experiments
