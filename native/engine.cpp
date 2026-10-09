// One long-lived llama.cpp instance. JSONL pipes preserve the Jev token readout;
// HTTP, tokenization, and calibrated decision formatting remain in the gateway.
#include "llama.h"
#include "ggml-backend.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

using json = nlohmann::json;

static int run_engine(int argc, char ** argv) {
    if (argc != 5) {
        std::cerr << "usage: system1-native MODEL CONTEXT THREADS GPU_LAYERS\n";
        return 2;
    }
    llama_model * model = nullptr;
    llama_context * ctx = nullptr;
    llama_batch batch = {};
    bool allocated = false;
    int result = 0;
    try {
        const int context = std::stoi(argv[2]), threads = std::stoi(argv[3]);
        if (context < 256 || threads < 1) throw std::runtime_error("invalid context/threads");
        ggml_backend_load_all();
        llama_backend_init();
        auto mp = llama_model_default_params();
        mp.n_gpu_layers = std::stoi(argv[4]);
        if (mp.n_gpu_layers != 0 && !llama_supports_gpu_offload())
            throw std::runtime_error("GPU offload requested but this native build has no GPU backend");
        model = llama_model_load_from_file(argv[1], mp);
        if (!model) throw std::runtime_error("model load failed");
        auto cp = llama_context_default_params();
        cp.n_ctx = context;
        cp.n_batch = cp.n_ubatch = std::min(512, context);
        cp.n_seq_max = 1;
        cp.n_threads = cp.n_threads_batch = threads;
        ctx = llama_init_from_model(model, cp);
        if (!ctx) throw std::runtime_error("context creation failed");
        batch = llama_batch_init(cp.n_batch, 0, 1);
        allocated = true;
        const int vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));
        std::cout << json({{"ready", true}, {"context", llama_n_ctx(ctx)}, {"vocab", vocab}}).dump() << std::endl;
        std::string line;
        while (std::getline(std::cin, line)) {
            try {
                // Bounded transport, then validate every ID before passing to C API.
                if (line.size() > size_t(context) * 16 + 4096) throw std::runtime_error("request too large");
                auto request = json::parse(line);
                auto tokens = request.at("tokens").get<std::vector<llama_token>>();
                auto letters = request.at("letters").get<std::vector<llama_token>>();
                if (tokens.empty() || tokens.size() > llama_n_ctx(ctx) || letters.empty() || letters.size() > 26)
                    throw std::runtime_error("invalid token/letter count");
                for (auto token : tokens) if (token < 0 || token >= vocab) throw std::runtime_error("invalid input token");
                for (auto token : letters) if (token < 0 || token >= vocab) throw std::runtime_error("invalid letter token");
                llama_memory_clear(llama_get_memory(ctx), true);
                for (size_t offset = 0; offset < tokens.size(); offset += cp.n_batch) {
                    batch.n_tokens = std::min(size_t(cp.n_batch), tokens.size() - offset);
                    for (int i = 0; i < batch.n_tokens; ++i) {
                        batch.token[i] = tokens[offset + i];
                        batch.pos[i] = offset + i;
                        batch.n_seq_id[i] = 1;
                        batch.seq_id[i][0] = 0;
                        batch.logits[i] = offset + i + 1 == tokens.size();
                    }
                    if (llama_decode(ctx, batch) != 0) throw std::runtime_error("native decode failed");
                }
                const auto * logits = llama_get_logits_ith(ctx, -1);
                if (!logits) throw std::runtime_error("missing logits");
                std::vector<float> output;
                for (auto token : letters) {
                    if (!std::isfinite(logits[token])) throw std::runtime_error("nonfinite logits");
                    output.push_back(logits[token]);
                }
                std::cout << json({{"logits", output}}).dump() << std::endl;
            } catch (const std::exception & error) {
                std::cout << json({{"error", error.what()}}).dump() << std::endl;
            }
        }
    } catch (const std::exception & error) {
        std::cerr << "fatal: " << error.what() << '\n';
        std::cout << json({{"error", error.what()}}).dump() << std::endl;
        result = 1;
    }
    if (allocated) llama_batch_free(batch);
    if (ctx) llama_free(ctx);
    if (model) llama_model_free(model);
    llama_backend_free();
    return result;
}

#ifdef _WIN32
int wmain(int argc, wchar_t ** wide_argv) {
    std::vector<std::string> arguments;
    for (int i = 0; i < argc; ++i) {
        const int size = WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, nullptr, 0, nullptr, nullptr);
        if (!size) return 2;
        std::string value(size, '\0');
        WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, value.data(), size, nullptr, nullptr);
        value.resize(size - 1);
        arguments.push_back(std::move(value));
    }
    std::vector<char *> argv;
    for (auto & argument : arguments) argv.push_back(argument.data());
    return run_engine(argc, argv.data());
}
#else
int main(int argc, char ** argv) { return run_engine(argc, argv); }
#endif
