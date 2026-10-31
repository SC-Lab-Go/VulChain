# RQ1 controlled DOT-assembly scaling results

Created: 2026-10-15  
Version: v2026.10.15-01

## Execution and integrity

The successful suite ran sequentially on authorized local server `<REDACTED_GRAPH_SERVER_HOST>`.
The host had 128 logical AMD EPYC 9334 CPUs, approximately 1.1 TiB RAM, 732
GiB free disk, no scheduler command/environment, and four idle NVIDIA L40S
GPUs. The builder is single-process and CPU-bound; GPUs were not used. Load and
pressure snapshots are preserved before and after every run.

The first launch (`results-local-20261015-scaling-01`) stopped before assembly
because of a strict-shell variable-initialization bug. The second
(`results-local-20261015-scaling-02`) stopped after a 1.75-second partial 25%
attempt because the archived release builder enforces full-release counts.
Both failed directories are preserved. The successful `-03` suite used the
same benchmark-only builder for every size; it imports the release schema,
family order, endpoint-type validation, and serialization and omits only fixed
release-cardinality assertions.

All nine stderr files are empty. Repeated outputs are byte-identical within
each size. All three 100% outputs match the official October 2 release SHA-256.
Independent line counts are 1,943,971, 3,887,939, and 7,775,876 respectively:
in each case exactly the edge count plus the four-line DOT wrapper.

## Individual runs

| Size | Run | Wall s | Peak RSS GiB | Throughput edges/s |
|---:|---:|---:|---:|---:|
| 25% | 1 | 13.12 | 0.206863 | 148,168.2 |
| 25% | 2 | 13.41 | 0.206543 | 144,964.0 |
| 25% | 3 | 13.36 | 0.206318 | 145,506.5 |
| 50% | 1 | 26.81 | 0.326195 | 145,018.1 |
| 50% | 2 | 26.57 | 0.326202 | 146,328.0 |
| 50% | 3 | 26.36 | 0.326176 | 147,493.7 |
| 100% | 1 | 54.36 | 0.446472 | 143,044.0 |
| 100% | 2 | 53.21 | 0.446789 | 146,135.5 |
| 100% | 3 | 52.45 | 0.446465 | 148,253.0 |

## Aggregate results

Standard deviations are sample standard deviations (n=3).

| Size | Edges | Nodes | Wall mean ± SD s (CV) | RSS mean ± SD GiB (CV) | Throughput mean ± SD edges/s (CV) |
|---:|---:|---:|---:|---:|---:|
| 25% | 1,943,967 | 1,480,204 | 13.297 ± 0.155 (1.166%) | 0.206575 ± 0.000274 (0.133%) | 146,213 ± 1,715 (1.173%) |
| 50% | 3,887,935 | 2,273,877 | 26.580 ± 0.225 (0.847%) | 0.326191 ± 0.000014 (0.004%) | 146,280 ± 1,239 (0.847%) |
| 100% | 7,775,872 | 3,137,207 | 53.340 ± 0.962 (1.803%) | 0.446575 ± 0.000185 (0.041%) | 145,811 ± 2,620 (1.797%) |

| Size | Input bytes | Output bytes | SHA-256 |
|---:|---:|---:|---|
| 25% | 165,851,251 | 255,182,716 | `46b392134fe3d097a1ea9bc4e8eadd1e351be06040cbb76c5b82e5329aa68ec9` |
| 50% | 331,703,290 | 510,365,797 | `844e48647766b74ec26a9ff79a8f361d8cf1ab99d33d2d653569b311b2c7bb1f` |
| 100% | 663,327,124 | 1,020,652,753 | `348d92cd4fe9cd49254fadec499b8bc8e80bba167ad97b82d03b1b24085b694b` |

## Interpretation

Measured wall time is approximately proportional over these three sizes:
doubling 25% to 50% multiplies mean time by 1.999; doubling 50% to 100%
multiplies it by 2.007; and throughput remains between approximately 145.8k
and 146.3k edges/s. This is empirical behavior for one builder, host, snapshot,
and three sizes—not a theoretical or general linear-scalability claim.

Peak RSS is not proportional to input size. Relative to 25%, a fourfold input
has only 2.16 times the peak RSS. The measured growth is subproportional,
consistent with fixed interpreter/state overhead and repeated graph endpoints.
Only three sizes were tested, so no asymptotic memory claim is warranted.
