from pyxdf import match_streaminfos, resolve_streams
from mnelab.io.xdf import read_raw_xdf
import mne
import mnelab

from attention_monitoring import startSession
from src.data_analysis.block import GradCPTSession
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib

infoFile = "C:\\Users\\HP User\\source\\repos\\attention-monitoring\\attention_monitoring\\src\\data\\gradCPT_sessions\\S73_040823_PTiaan\\info.json"
sess = GradCPTSession(infoFile)

raw = read_raw_xdf(sess.blocks["full_block_1"].dataFile, stream_ids=[3])
raw.plot()