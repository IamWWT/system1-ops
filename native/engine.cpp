// One long-lived llama.cpp instance. JSONL pipes preserve the Jev token readout;
// HTTP, tokenization, and calibrated decision formatting remain in the gateway.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "ggml-backend.h"
#include "llama.h"
#include "nlohmann/json.hpp"
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <dlfcn.h>
#include <unistd.h>
#endif

using json = nlohmann::json;

#ifdef _WIN32
static std::string executable_dir() {
    char buffer[4096];
    const long size = GetModuleFileNameA(nullptr, buffer, sizeof(buffer) - 1);
    if (size <= 0) return {};
    std::string path(buffer, size);
    const auto pos = path.find_last_of("\\/");
    return pos == std::string::npos ? "" : path.substr(0, pos + 1);
}
#else
static std::string executable_dir() {
    char buffer[4096];
    const long size = readlink("/proc/self/exe", buffer, sizeof(buffer) - 1);
    if (size <= 0) return {};
    std::string path(buffer, size);
    const auto pos = path.find_last_of('/');
    return pos == std::string::npos ? "" : path.substr(0, pos + 1);
}
#endif

#ifdef _WIN32
using dl_handle = void*;
static dl_handle open_library(const std::string& path) { return LoadLibraryA(path.c_str()); }
static void close_library(dl_handle handle) {
    if (handle) FreeLibrary(handle);
}
static void* find_symbol(dl_handle handle, const char* name) { return GetProcAddress((HMODULE)handle, name); }
#else
using dl_handle = void*;
static dl_handle open_library(const std::string& path) { return dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL); }
static void close_library(dl_handle handle) {
    if (handle) dlclose(handle);
}
static void* find_symbol(dl_handle handle, const char* name) { return dlsym(handle, name); }
#endif

// Pick the CPU backend plugin that best matches this machine, mirroring ggml's
// own score-based selection, without loading GPU plugins. Loading all plugins
// (the old behavior) initializes CUDA even with zero offloaded layers, which
// fails or steals VRAM while another service occupies the GPU.
static std::string select_cpu_backend() {
    const std::string directory = executable_dir();
    if (directory.empty()) return {};
    std::string best;
    int best_score = -1;
    std::error_code ec;
    for (const auto& entry : std::filesystem::directory_iterator(directory, ec)) {
        std::error_code check_ec;
        if (!entry.is_regular_file(check_ec) || check_ec) continue;
        const std::string name = entry.path().filename().string();
        if (name.rfind("libggml-cpu-", 0) != 0) continue;
#ifdef _WIN32
        const bool suffix_ok = name.size() >= 4 && name.substr(name.size() - 4) == ".dll";
#else
        const bool suffix_ok = name.size() >= 3 && name.substr(name.size() - 3) == ".so";
#endif
        if (!suffix_ok) continue;
        const std::string path = entry.path().string();
        dl_handle handle = open_library(path);
        if (!handle) continue;
        auto score_fn = reinterpret_cast<int (*)()>(find_symbol(handle, "ggml_backend_score"));
        const int score = score_fn ? score_fn() : 0;
        close_library(handle);
        if (score > best_score) {
            best_score = score;
            best = path;
        }
    }
    return best;
}

static void init_backends(const int gpu_layers) {
    if (gpu_layers > 0) {
        ggml_backend_load_all();
        return;
    }
    const std::string cpu = select_cpu_backend();
    if (cpu.empty()) throw std::runtime_error("CPU backend plugin (libggml-cpu-*) not found next to system1-native");
    if (!ggml_backend_load(cpu.c_str())) throw std::runtime_error("failed to load CPU backend " + cpu);
}

static int run_engine(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: system1-native MODEL CONTEXT THREADS GPU_LAYERS\n";
        return 2;
    }
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    llama_batch batch = {};
    bool allocated = false;
    int result = 0;
    try {
        const int context = std::stoi(argv[2]), threads = std::stoi(argv[3]);
        const int gpu_layers = std::stoi(argv[4]);
        if (context < 256 || threads < 1) throw std::runtime_error("invalid context/threads");
        init_backends(gpu_layers);
        llama_backend_init();
        auto mp = llama_model_default_params();
        mp.n_gpu_layers = gpu_layers;
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
                for (auto token : tokens)
                    if (token < 0 || token >= vocab) throw std::runtime_error("invalid input token");
                for (auto token : letters)
                    if (token < 0 || token >= vocab) throw std::runtime_error("invalid letter token");
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
                const auto* logits = llama_get_logits_ith(ctx, -1);
                if (!logits) throw std::runtime_error("missing logits");
                std::vector<float> output;
                for (auto token : letters) {
                    if (!std::isfinite(logits[token])) throw std::runtime_error("nonfinite logits");
                    output.push_back(logits[token]);
                }
                std::cout << json({{"logits", output}}).dump() << std::endl;
            } catch (const std::exception& error) {
                std::cout << json({{"error", error.what()}}).dump() << std::endl;
            }
        }
    } catch (const std::exception& error) {
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
int wmain(int argc, wchar_t** wide_argv) {
    std::vector<std::string> arguments;
    for (int i = 0; i < argc; ++i) {
        const int size = WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, nullptr, 0, nullptr, nullptr);
        if (!size) return 2;
        std::string value(size, '\0');
        WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, value.data(), size, nullptr, nullptr);
        value.resize(size - 1);
        arguments.push_back(std::move(value));
    }
    std::vector<char*> argv;
    for (auto& argument : arguments) argv.push_back(argument.data());
    return run_engine(argc, argv.data());
}
#else
int main(int argc, char** argv) { return run_engine(argc, argv); }
#endif
