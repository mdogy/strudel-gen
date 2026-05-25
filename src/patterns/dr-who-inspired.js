setcpm(18)
stack(
  note("e1 d1 e1 d1 e1 d1 c1 d1").s("sawtooth")
    .lpf("<220 380 220 380 220 380 180 380>")
    .room(0.93).size(0.97)
    .gain(0.4).slow(5).orbit(0),

  note("b4 ~ ~ d5 e5 ~ d5 ~ b4 ~ ~ e4 g4 ~ a4 ~").s("sine")
    .room(0.88).size(0.94)
    .delay(0.45).delayt(0.666).delayfb(0.55)
    .gain(0.24).slow(4).orbit(1),

  note("e3,g3,b3").s("sine")
    .room(0.91).size(0.96)
    .sometimes(x => x.speed("<0.5 1 2>"))
    .gain(0.15).slow(10).orbit(2)
)
