let cpm = 135;
let a = note("c2").s("supersaw").lpf(400).room(0.8).slow(8);
let b = stack(a, note("eb3").s("sine").room(0.7).slow(6));
arrange([4, a], [2, b])