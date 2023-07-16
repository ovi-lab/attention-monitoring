import pyxdf

def dataVis(dataPath):
    """Visualize data collected during a gradCPT session.

    Parameters
    ----------
    dataPath : str
        The path to `xdf` file containing the data.

    """

    data, header = pyxdf.load_xdf

    return None


if __name__ == '__main__':
    dataVis()