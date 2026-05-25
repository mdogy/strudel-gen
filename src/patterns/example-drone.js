setcpm(20)
stack(
  note("<c2 c2 g2 f2>").s("sawtooth")
    .lpf(400).room(0.9).size(0.95)
    .gain(0.4).slow(8).orbit(0),

  note("<c4 ~ eb4 ~ g4 ~ f4 ~>").s("sine")
    .room(0.8).gain(0.3).slow(4).orbit(1),

  note("c3,g3,eb3").s("pad")
    .room(0.85).delay(0.4).delayt(0.5).delayfb(0.5)
    .gain(0.5).slow(6).orbit(2)
)
