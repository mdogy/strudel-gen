// Dr. Who-inspired theme — sweeping bass + theremin lead + pad
setcpm(80)
stack(
  note("e1 d1 e1 d1 e1 d1 c1 d1").s("sine").lpf(220).room(0.9).slow(4).orbit(0),
  note("b4 d5 e5 d5 b4 e4 g4 a4").s("sine").vib(4).vibdepth(0.01).room(0.88).slow(4).orbit(1),
  note("e3,g3,b3").s("sine").room(0.92).gain(0.14).slow(8).orbit(2)
)
