import pstats
import sys

p = pstats.Stats('profile.out')
p.strip_dirs().sort_stats('cumulative').print_stats(30)
p.sort_stats('time').print_stats(30)
