import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Union

from pygenomeviz import Genbank, GenomeViz, __version__
from pygenomeviz.align import Align, AlignCoord
from pygenomeviz.scripts import get_argparser, print_args


def main():
    """Main function called from CLI"""
    # Get arguments
    args = get_args()
    print_args(args)
    # Run workflow
    run(**args.__dict__)


def run(
    # General options
    gbk_files: List[Union[str, Path]],
    outdir: Union[str, Path],
    format: str = "png",
    reuse: bool = False,
    # MUMmer alignment options
    seqtype: str = "protein",
    maptype: str = "many-to-many",
    min_length: int = 0,
    min_identity: float = 0,
    # Figure appearence options
    fig_width: float = 15,
    fig_track_height: float = 1.0,
    feature_track_ratio: float = 1.0,
    link_track_ratio: float = 5.0,
    tick_track_ratio: float = 1.0,
    track_labelsize: int = 20,
    tick_labelsize: int = 15,
    normal_link_color: str = "grey",
    inverted_link_color: str = "red",
    align_type: str = "center",
    tick_style: Optional[str] = None,
    feature_plotstyle: str = "bigarrow",
    arrow_shaft_ratio: float = 0.5,
    feature_color: str = "orange",
    feature_linewidth: float = 0,
    curve: bool = True,
) -> GenomeViz:
    """Run genome visualization workflow using MUMmer

    Parameters
    ----------
    gbk_files : List[Union[str, Path]]
        Input genome genbank files
    outdir : Union[str, Path]
        Output directory
    format : str, optional
        Output image format (`png`|`jpg`|`svg`|`pdf`)
    reuse : bool, optional
        If True, reuse previous result if available
    seqtype : str, optional
        MUMmer alignment sequence type (`protein`|`nucleotide`)
    maptype : str, optional
        MUMmer alignment map type (`many-to-many`|`one-to-one`)
    min_length : int, optional
        Min-length threshold to be plotted
    min_identity : float, optional
        Min-identity threshold to be plotted
    fig_width : float, optional
        Figure width
    fig_track_height : float, optional
        Figure track height
    feature_track_ratio : float, optional
        Feature track ratio
    link_track_ratio : float, optional
        Link track ratio
    tick_track_ratio : float, optional
        Tick track ratio
    track_labelsize : int, optional
        Track label size
    tick_labelsize : int, optional
        Tick label size
    normal_link_color : str, optional
        Normal link color
    inverted_link_color : str, optional
        Inverted link color
    align_type : str, optional
        Figure tracks align type (`left`|`center`|`right`)
    tick_style : Optional[str], optional
        Tick style (`bar`|`axis`|`None`)
    feature_plotstyle : str, optional
        Feature plotstyle (`bigarrow`|`arrow`)
    arrow_shaft_ratio : float, optional
        Feature arrow shaft ratio
    feature_color : str, optional
        Feature color
    feature_linewidth : float, optional
        Feature edge line width
    curve : bool, optional
        If True, plot curved style link

    Returns
    -------
    GenomeViz
        _description_
    """
    # Check MUMmer installation
    Align.check_installation()

    # Setup output contents
    outdir = Path(outdir)
    os.makedirs(outdir, exist_ok=True)
    result_fig_file = outdir / f"result.{format}"
    align_coords_file = outdir / "align_coords.tsv"

    # Set tracks & features
    gv = GenomeViz(
        fig_width=fig_width,
        fig_track_height=fig_track_height,
        feature_track_ratio=feature_track_ratio,
        link_track_ratio=link_track_ratio,
        tick_track_ratio=tick_track_ratio,
        align_type=align_type,
        tick_style=tick_style,
        tick_labelsize=tick_labelsize,
        plot_size_thr=0.0005,
    )
    gbk_list = [Genbank(f) for f in gbk_files]
    for gbk in gbk_list:
        track = gv.add_feature_track(gbk.name, gbk.genome_length, track_labelsize)
        track.add_genbank_features(
            gbk,
            feature_type="CDS",
            plotstyle=feature_plotstyle,
            arrow_shaft_ratio=arrow_shaft_ratio,
            facecolor=feature_color,
            linewidth=feature_linewidth,
        )

    # MUMmer alignment
    if align_coords_file.exists() and reuse:
        print("Reuse previous MUMmer result.")
        align_coords = AlignCoord.read(align_coords_file)
    else:
        with TemporaryDirectory() as tmpdir:
            align_coords = Align(gbk_list, tmpdir, seqtype, maptype).run()
            AlignCoord.write(align_coords, align_coords_file)
    align_coords = AlignCoord.filter(align_coords, min_length, min_identity)

    # Set links
    min_identity = int(min([ac.identity for ac in align_coords]))
    for ac in align_coords:
        link1 = (ac.ref_name, ac.ref_start, ac.ref_end)
        link2 = (ac.query_name, ac.query_start, ac.query_end)
        gv.add_link(
            link1,
            link2,
            normal_link_color,
            inverted_link_color,
            curve=curve,
            v=ac.identity,
            vmin=min_identity,
        )

    # Plot figure
    fig = gv.plotfig(dpi=300)

    # Set colorbar
    bar_colors = [normal_link_color]
    contain_inverted_align = any([ac.is_inverted for ac in align_coords])
    if contain_inverted_align:
        bar_colors.append(inverted_link_color)
    gv.set_colorbar(fig, bar_colors, vmin=min_identity)

    # Save figure
    fig.savefig(result_fig_file, bbox_inches="tight", pad_inches=0.5)
    print(f"\nSave result figure ({result_fig_file}).")

    return gv


def get_args(cli_args: Optional[List[str]] = None) -> argparse.Namespace:
    """Get arguments

    Parameters
    ----------
    cli_args : Optional[List[str]], optional
        CLI arguments (Used in unittest)

    Returns
    -------
    args : argparse.Namespace
        Argument parameters
    """
    parser = get_argparser(prog_name="MUMmer")

    #######################################################
    # General options
    #######################################################
    general_opts = parser.add_argument_group("General Options")
    general_opts.add_argument(
        "--gbk_files",
        type=str,
        help="Input genome genbank files",
        nargs="+",
        required=True,
        metavar="IN",
    )
    general_opts.add_argument(
        "-o",
        "--outdir",
        type=str,
        help="Output directory",
        required=True,
        metavar="OUT",
    )
    default_format = "png"
    format_list = ["png", "jpg", "svg", "pdf"]
    general_opts.add_argument(
        "--format",
        type=str,
        help="Output image format ('png'[*]|'jpg'|'svg'|'pdf')",
        default=default_format,
        choices=format_list,
        metavar="",
    )
    general_opts.add_argument(
        "--reuse",
        help="Reuse previous result if available",
        action="store_true",
    )
    general_opts.add_argument(
        "-v",
        "--version",
        version=f"v{__version__}",
        help="Print version information",
        action="version",
    )
    general_opts.add_argument(
        "-h",
        "--help",
        help="Show this help message and exit",
        action="help",
    )
    #######################################################
    # MUMmer alignment options
    #######################################################
    mummer_alignment_opts = parser.add_argument_group("MUMmer Alignment Options")
    defaullt_seqtype = "protein"
    mummer_alignment_opts.add_argument(
        "--seqtype",
        type=str,
        help="MUMmer alignment sequence type ('protein'[*]|'nucleotide')",
        default=defaullt_seqtype,
        choices=["nucleotide", "protein"],
        metavar="",
    )
    default_maptype = "many-to-many"
    mummer_alignment_opts.add_argument(
        "--maptype",
        type=str,
        help="MUMmer alignment map type ('many-to-many'[*]|'one-to-one')",
        default=default_maptype,
        choices=["one-to-one", "many-to-many"],
        metavar="",
    )
    default_min_length = 0
    mummer_alignment_opts.add_argument(
        "--min_length",
        type=int,
        help=f"Min-length threshold to be plotted (Default: {default_min_length})",
        default=default_min_length,
        metavar="",
    )
    default_min_identity = 0
    mummer_alignment_opts.add_argument(
        "--min_identity",
        type=float,
        help=f"Min-identity threshold to be plotted (Default: {default_min_identity})",
        default=default_min_identity,
        metavar="",
    )
    #######################################################
    # Figure appearence options
    #######################################################
    fig_opts = parser.add_argument_group("Figure Appearence Options")
    default_fig_width = 15
    fig_opts.add_argument(
        "--fig_width",
        type=float,
        help=f"Figure width (Default: {default_fig_width})",
        default=default_fig_width,
        metavar="",
    )
    default_fig_track_height = 1.0
    fig_opts.add_argument(
        "--fig_track_height",
        type=float,
        help=f"Figure track height (Default: {default_fig_track_height})",
        default=default_fig_track_height,
        metavar="",
    )
    default_feature_track_ratio = 1.0
    fig_opts.add_argument(
        "--feature_track_ratio",
        type=float,
        help=f"Feature track ratio (Default: {default_feature_track_ratio})",
        default=default_feature_track_ratio,
        metavar="",
    )
    default_link_track_ratio = 5.0
    fig_opts.add_argument(
        "--link_track_ratio",
        type=float,
        help=f"Link track ratio (Default: {default_link_track_ratio})",
        default=default_link_track_ratio,
        metavar="",
    )
    default_tick_track_ratio = 1.0
    fig_opts.add_argument(
        "--tick_track_ratio",
        type=float,
        help=f"Tick track ratio (Default: {default_tick_track_ratio})",
        default=default_tick_track_ratio,
        metavar="",
    )
    default_track_labelsize = 20
    fig_opts.add_argument(
        "--track_labelsize",
        type=int,
        help=f"Track label size (Default: {default_track_labelsize})",
        default=default_track_labelsize,
        metavar="",
    )
    default_tick_labelsize = 15
    fig_opts.add_argument(
        "--tick_labelsize",
        type=int,
        help=f"Tick label size (Default: {default_tick_labelsize})",
        default=default_tick_labelsize,
        metavar="",
    )
    default_normal_link_color = "grey"
    fig_opts.add_argument(
        "--normal_link_color",
        type=str,
        help=f"Normal link color (Default: '{default_normal_link_color}')",
        default=default_normal_link_color,
        metavar="",
    )
    default_inverted_link_color = "red"
    fig_opts.add_argument(
        "--inverted_link_color",
        type=str,
        help=f"Inverted link color (Default: '{default_inverted_link_color}')",
        default=default_inverted_link_color,
        metavar="",
    )
    default_align_type = "center"
    align_type_list = ["left", "center", "right"]
    fig_opts.add_argument(
        "--align_type",
        type=str,
        help="Figure tracks align type ('left'|'center'[*]|'right')",
        default=default_align_type,
        choices=align_type_list,
        metavar="",
    )
    default_tick_style = None
    fig_opts.add_argument(
        "--tick_style",
        type=str,
        help="Tick style ('bar'|'axis'|None[*])",
        default=default_tick_style,
        choices=["bar", "axis"],
        metavar="",
    )
    feature_plotstyle = "bigarrow"
    feature_plotstyle_list = ["bigarrow", "arrow"]
    fig_opts.add_argument(
        "--feature_plotstyle",
        type=str,
        help="Feature plot style ('bigarrow'[*]|'arrow')",
        default=feature_plotstyle,
        choices=feature_plotstyle_list,
        metavar="",
    )
    default_arrow_shaft_ratio = 0.5
    fig_opts.add_argument(
        "--arrow_shaft_ratio",
        type=float,
        help=f"Feature arrow shaft ratio (Default: {default_arrow_shaft_ratio})",
        default=default_arrow_shaft_ratio,
        metavar="",
    )
    default_feature_color = "orange"
    fig_opts.add_argument(
        "--feature_color",
        type=str,
        help=f"Feature color (Default: '{default_feature_color}')",
        default=default_feature_color,
        metavar="",
    )
    default_feature_linewidth = 0.0
    fig_opts.add_argument(
        "--feature_linewidth",
        type=float,
        help=f"Feature edge line width (Default: {default_feature_linewidth})",
        default=default_feature_linewidth,
        metavar="",
    )
    fig_opts.add_argument(
        "--curve",
        help="Plot curved style link (Default: OFF)",
        action="store_true",
    )
    args = parser.parse_args(cli_args)

    # Check arguments
    err_info = ""
    if len(args.gbk_files) < 2:
        err_info += "--gbk_files must be set at least two files.\n"
    for file in args.gbk_files:
        if not os.path.isfile(file):
            err_info += f"File not found '{file}'.\n"

    if err_info != "":
        parser.error("\n" + err_info)

    return args


if __name__ == "__main__":
    main()
