# Third-party inference components

System1 Ops does not redistribute weights or vendor source. Downloaded sources
and weights stay outside Git. Their upstream licenses and notices still apply.

* [Laya](https://github.com/NandhaKishorM/laya), Apache-2.0,
  pinned commit `1adc59f7e371deb601fcfa18a14e25db238addcc`.
* [StartLux Decision](https://github.com/StartLuxLabs/StartLux-Decision), Apache-2.0,
  pinned commit `0e7a2e81b9c92756e26d8edd843a44d50e362669`.
  `startlux_policy.py` adapts its model-loading boundary. Jev rendering, decision
  types and probability calibration remain in the upstream implementation.
* [llama.cpp](https://github.com/ggml-org/llama.cpp), MIT,
  pinned commit `89fe24240548456477870b2a627cd8021fea1e39`.
  The original native pipe driver links to its C API and includes its vendored
  nlohmann/json headers (MIT). Retain upstream LICENSE files when distributing binaries.
* StartLux weights include their own LICENSE and NOTICE; conversion/quantization
  does not replace those terms. No weights are published in this repository.

Other runtime dependencies retain their respective licenses.
