// Minimal MuJoCo C++ harness: load a model, step it, report where time goes.
//
// JD: "Write clean, performant code in Python and/or C++ to support simulation
// infrastructure" and "Profile and optimize simulation performance."
//
// The Python bindings are fine for experiments, but simulation INFRASTRUCTURE
// -- the thing that runs inside a training loop or a CI job -- usually is not
// Python. This is the C++ side: no bindings, no interpreter, direct mj_step,
// and per-phase timing from MuJoCo's own instrumentation.
//
// Build:
//   c++ -std=c++17 -O2 sim_bench.cpp -lmujoco -o sim_bench
// Run:
//   ./sim_bench model.xml 5000

#include <mujoco/mujoco.h>

#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

// MuJoCo's per-phase timers are OPT-IN: it calls mjcb_time to read the clock,
// and if you never install one the whole timer array stays zero. That is easy
// to mistake for "profiling says the solver is free". Install a real
// high-resolution clock.
mjtNum HighResSeconds() {
  using clock = std::chrono::steady_clock;
  static const auto t0 = clock::now();
  return std::chrono::duration<double>(clock::now() - t0).count();
}


// MuJoCo exposes a per-phase timer array. Reading it is far more informative
// than wall-clock alone: it says whether you are bound by collision detection,
// the constraint solver, or plain integration -- which determines what you can
// actually do about it.
struct PhaseTimes {
  double total_ms = 0, collision_ms = 0, prepare_ms = 0, solve_ms = 0, other_ms = 0;
};

PhaseTimes ReadTimers(const mjData* d, int nstep) {
  PhaseTimes p;
  const double n = nstep > 0 ? nstep : 1;
  // mjcb_time returns SECONDS, so durations are seconds -> ms is x1000
  p.total_ms     = 1e3 * d->timer[mjTIMER_STEP].duration / n;
  p.collision_ms = 1e3 * d->timer[mjTIMER_POS_COLLISION].duration / n;
  p.prepare_ms   = 1e3 * d->timer[mjTIMER_POS_MAKE].duration / n;
  p.solve_ms     = 1e3 * d->timer[mjTIMER_CONSTRAINT].duration / n;
  p.other_ms     = p.total_ms - (p.collision_ms + p.prepare_ms + p.solve_ms);
  return p;
}

double Percent(double part, double whole) {
  return whole > 0 ? 100.0 * part / whole : 0.0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s <model.xml> [nsteps]\n", argv[0]);
    return 1;
  }
  const int nsteps = argc > 2 ? std::atoi(argv[2]) : 5000;

  char error[1024] = "";
  mjModel* m = mj_loadXML(argv[1], nullptr, error, sizeof(error));
  if (!m) {
    std::fprintf(stderr, "load failed: %s\n", error);
    return 1;
  }
  mjData* d = mj_makeData(m);

  // enable internal profiling before any stepping
  mjcb_time = HighResSeconds;

  std::printf("model      : %s\n", argv[1]);
  // mjtSize is 64-bit in MuJoCo 3.x; cast rather than assume int
  std::printf("  nq=%d nv=%d nu=%d nbody=%d ngeom=%d\n",
              static_cast<int>(m->nq), static_cast<int>(m->nv),
              static_cast<int>(m->nu), static_cast<int>(m->nbody),
              static_cast<int>(m->ngeom));
  std::printf("  timestep=%.6f  integrator=%d\n\n", m->opt.timestep, m->opt.integrator);

  // Warm up: the first steps allocate and populate caches. Timing them
  // reports startup cost as if it were steady-state throughput.
  for (int i = 0; i < 100; ++i) mj_step(m, d);
  mj_resetData(m, d);
  // mj_resetData already clears the timer array; the earlier reinterpret_cast
  // into it was unnecessary and not type-safe.

  const auto t0 = std::chrono::steady_clock::now();
  for (int i = 0; i < nsteps; ++i) mj_step(m, d);
  const auto t1 = std::chrono::steady_clock::now();

  const double wall_s = std::chrono::duration<double>(t1 - t0).count();
  const double sim_s  = nsteps * m->opt.timestep;
  const PhaseTimes p  = ReadTimers(d, nsteps);

  std::printf("steps        : %d\n", nsteps);
  std::printf("wall clock   : %.4f s\n", wall_s);
  std::printf("throughput   : %.1f steps/s\n", nsteps / wall_s);
  std::printf("realtime     : %.2fx\n\n", sim_s / wall_s);

  std::printf("per-step breakdown (MuJoCo internal timers)\n");
  std::printf("  collision  : %8.4f ms  (%5.1f%%)\n",
              p.collision_ms, Percent(p.collision_ms, p.total_ms));
  std::printf("  make cnstr : %8.4f ms  (%5.1f%%)\n",
              p.prepare_ms, Percent(p.prepare_ms, p.total_ms));
  std::printf("  solve      : %8.4f ms  (%5.1f%%)\n",
              p.solve_ms, Percent(p.solve_ms, p.total_ms));
  std::printf("  other      : %8.4f ms  (%5.1f%%)\n",
              p.other_ms, Percent(p.other_ms, p.total_ms));
  std::printf("  TOTAL      : %8.4f ms\n\n", p.total_ms);

  std::printf("final state  : ncon=%d  qpos[0]=%.6f\n",
              static_cast<int>(d->ncon), m->nq ? d->qpos[0] : 0.0);

  mj_deleteData(d);
  mj_deleteModel(m);
  return 0;
}
