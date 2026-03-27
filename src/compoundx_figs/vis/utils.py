from string import ascii_lowercase as alphabet

import matplotlib.axes
import matplotlib.cm
import seaborn as sns
from loguru import logger


def _set_styles():

    sns.set_style("ticks")
    sns.set_palette("deep")


def set_props(artist, **props) -> None:
    for key in props:
        setter_name = f"set_{key}"
        value = props[key]
        setter = getattr(artist, setter_name, None)
        if setter is None:
            logger.warning(f"Could not find {setter_name}")
        else:
            setter(value)


def clear_labels(ax: matplotlib.axes.Axes):
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("")
    ax.set_title("", loc="left")
    ax.set_title("", loc="right")


def number_subplot(ax, text, x="left", y="bottom", space=0.05, **text_props):
    """
    experimental function to place subplot text a fixed distance from corners
    """
    fig = ax.get_figure()
    w, h = fig.get_size_inches()
    p = ax.get_position()

    if x is None:
        x = space / w
    elif isinstance(x, str):
        if x == "left":
            x = space / w
        elif x == "right":
            x = 1 - space / w
        else:
            raise ValueError("x must be `left` or `right` if a string")
    if y is None:
        y = space / h
    elif isinstance(y, str):
        if y == "bottom":
            y = space / h
        elif y == "top":
            y = 1 - space / h
        else:
            raise ValueError("y must be `bottom` or `top` if a string")

    if x < 0.5:
        px = p.x0
        sx = 1
    else:
        px = p.x1
        sx = -1
        x = 1 - x

    if y < 0.5:
        py = p.y0
        sy = 1
    else:
        py = p.y1
        sy = -1
        y = 1 - y

    va = "top" if sy < 0 else "bottom"
    ha = "left" if sx > 0 else "right"

    dx = px + x * sx
    dy = py + y * sy

    text_props.update(zorder=max([c.get_zorder() for c in ax.get_children()]) + 1)
    ax.text(dx, dy, text, ha=ha, va=va, transform=fig.transFigure, **text_props)


def number_subplots(
    ax_list,
    label_list: list[str] = alphabet,
    x="left",
    y="top",
    space=0.05,
    braces=True,
    **text_props,
):
    """
    add subplot numbers a fixed distance from given corners. Label list defaults

    Parameters
    ----------
    ax_list : list
        axes objects with a get_position and text function
    label_list : iterable
        a list or string of iterable objects. If no round brackets, then add them
    x: float/str/None
        the location of the label. If string, left or right
    y: float/str/None
        the location of the label. If string, top or bottom
    space: float
        the default spacing from the given corner (scales relative to figure)
    """
    for ax, lbl in zip(ax_list, label_list):
        lbl = str(lbl)
        if ("(" not in lbl) and (")" not in lbl) and braces:
            lbl = f"({lbl})"
        number_subplot(ax, lbl, x=x, y=y, space=space, **text_props)


def save_figures_to_pdf(fig_list, pdf_name, **savefig_kwargs):
    """
    Saves a list of figure objects to a pdf with multiple pages.
    Parameters
    ----------
    fig_list : list
        list of figure objects
    pdf_name : str
        path to save pdf to.
    savefig_kwargs : key-value pairs passed to ``Figure.savefig``
    Returns
    -------
    None
    """
    import matplotlib.backends.backend_pdf

    pdf = matplotlib.backends.backend_pdf.PdfPages(pdf_name)

    kwargs = dict(dpi=120)
    kwargs.update(savefig_kwargs)

    for fig in fig_list:  # will open an empty extra figure :(
        pdf.savefig(fig, **kwargs)

    pdf.close()
    plt.close("all")


_set_styles()
