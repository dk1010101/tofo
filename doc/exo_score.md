# Scoring ExoPlanets for Observing

The tool provides two bits of information that can be used to priorities exoplanets: `priority` which is the ExoClock observing priority ranging from `low` to `alert` and `score` which is tool-specific score.

The `score` parameter is composed as a (weighted) geometric average of a number of other scores. It uses total number of observations (the lower the better), the number of recent ExoClock observations (the fewer the better), the number of possible additional targets (the more the better), the smallest period in all possible additional targets (the shorter the better since small periods suggest higher likelihood of seeing something interesting) and the smallest duration in all possible additional targets (again, since short durations increase the possibility of observing all of it). There values are used to rank all targets and then the rankings are used to create overall ranking which are then transformed in to a number between 0.0 and 1.0 with 0.0 suggesting least interesting target and 1.0 the most interesting one. It is worth noting that it is possible for two exoplanet targets to have the same score. It is not an absolute overall ranking but a score created from rankings of above mentioned measures.

The scores are saved the the cache file and are thus easy to inspect using any HDF5 browsing tool.
