import panic

alarms = panic.api()

alarms.add('Rainfall',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/rainfall)',
           description='Rainfall in central telescope area.',
           receivers='kmadisa@ska.ac.za')
alarms.add('Outside_Temperature',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/temperature)',
           description='Current temperature outside near the telescope.',
           receivers='kmadisa@ska.ac.za')
alarms.add('Wind_speed',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/wind-speed)',
           description='Wind speed in central telescope area.',
           receivers='kmadisa@ska.ac.za')
alarms.add('Barometric_pressure',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/pressure)',
           description='Barometric pressure in central telescope area.',
           receivers='kmadisa@ska.ac.za')
alarms.add('Insolation',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/insolation)',
           description='Sun intensity in central telescope area.',
           receivers='kmadisa@ska.ac.za')
alarms.add('Air_humidity',
           'mkat/panic/kataware',
           formula='(mkat_sim/weather/1/relative-humidity)',
           description='Relative humidity in central telescope area.',
           receivers='kmadisa@ska.ac.za')
