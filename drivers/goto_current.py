import numpy as np
import k6220
import time
from time import sleep



def goto_current(current_aim):
	mykei = k6220.K6220("GPIB0::12::INSTR")
	mykei.set_limits(-0.04,0.04)
	mykei.write("SOUR:CURR:COMP {0}".format(10))
	
	current_now = mykei.get_current()
	step = 10e-6	# шаг, с которым пойдем по току = 10мкА
	######################
	# проверка на значение задаваемого тока
	if abs(current_aim) > 10e-3: 			
		print("error: Current, that you try to set is too much")
		return 0
	######################
	if mykei.get_current() == 0:
		mykei.output_on()
		sleep(0.1)
	#if mykei.output_stat == 0:
		#mykei.set_current_instant(0)
		#mykei.output_on()
	######################
	# вдруг, разница небольшая и можно сразу задать
	if abs(current_aim - current_now) < 3*step:
		mykei.set_current_instant(current_aim)
		if current_aim == 0:
			mykei.output_off()
		return 1
	######################
	#число шагов до цели
	num_step = int(np.round((abs(current_aim - current_now) / step),0))
	if current_aim < current_now:
		step = -step #направление движения по току
	# пошли менять ток
	for i in range(1,num_step):
		current_now = np.round((current_now + step),9)
		mykei.set_current_instant(current_now)
		print(mykei.get_current())
		#print("Current: {0:.2f} A".format(mykei.get_current()))
		sleep(0.2)
	# последний штрих, на случай, если чуть-чуть не попали
	if abs(mykei.get_current() - current_aim) < 3*abs(step):
		mykei.set_current_instant(current_aim)
		# если ток = 0, стоит вырубить прибор
	else: # паника, если сильно промахнулись
		print("error: miss!")
		if abs(mykei.get_current()) > 3e-3:
			mykei.output_off()
		return 0
	if mykei.get_current() == 0:
		mykei.output_off()
		return 1