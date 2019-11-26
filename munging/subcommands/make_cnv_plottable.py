"""
Munges the output of different CNV callers into a common .tsv output that is
usable by the plot_cnv subcommand.
"""

import argparse
import os
import pandas as pd
from munging.annotation import Transcript, GenomeIntervalTree

def build_parser(parser):
    parser.add_argument('cnv_data',
                        help='Path to the raw output from the CNV caller')
    parser.add_argument('package', choices=['contra', 'cnvkit'],
                        help='Software package used to create the CNV_data')
    parser.add_argument('-r', '--refgene',
                        help='Path to the transcript-filtered USCS RefSeq table file (used for annotation)')
    parser.add_argument('-o', '--outfile', 
                        help='Path to the out file (default <prefix>.<package>.CNV_plottable.tsv)')

def parse_contra_file(file_name):
    """
    ADD A DOCSTRNG
    """
    df_raw = pd.read_csv(file_name, sep='\t', header=0, dtype=str)
    df_plot = pd.DataFrame()
    df_plot['log2'] = df_raw['Adjusted.Mean.of.LogRatio']
    df_plot['chr'] = df_raw['Chr']
    df_plot['start_pos'] = df_raw['OriStCoordinate']
    df_plot['end_pos'] = df_raw['OriEndCoordinate']
    return df_plot

def parse_cnvkit_file(file_name):
    """
    ADD A DOCSTRING
    """
    df_raw = pd.read_csv(file_name, sep='\t', header=0, dtype=str)
    df_targets = df_raw[df_raw['gene'] != 'Antitarget']
    df_plot = pd.DataFrame()
    df_plot['log2'] = df_targets['log2']
    df_plot['chr'] = df_targets['chromosome']
    df_plot['start_pos'] = df_targets['start']
    df_plot['end_pos'] = df_targets['end']
    return df_plot

def add_annotations(df, genome_tree):
    """
    ADD A DOCSTRING
    """
    for i, row in df.iterrows():
        chrom = row['chr']
        start = int(row['start_pos'])
        end = int(row['end_pos']) + 1
        transcript_list = genome_tree[chrom][start:end]
        if transcript_list:
            t = transcript_list.pop()[2]
            df.at[i, 'gene'] = t.gene
            df.at[i, 'transcript'] = t.id
            exons = t.get_exons(start, end, report_utr=False)
            if exons:
                df.at[i, 'exon'] = str(exons[0])
        else:
            df.at[i, 'gene'] = 'intergenic'

def action(args):
    # import and parse the data
    if args.package == 'contra':
        df = parse_contra_file(args.cnv_data)
    elif args.package == 'cnvkit':
        df = parse_cnvkit_file(args.cnv_data)
    else:
        # should never hit here
        raise ValueError("Improper type specified as argument")

    # add annotations to the parsed data
    gt = GenomeIntervalTree.from_table(args.refgene)
    add_annotations(df, gt)

    # set the out file path
    if args.outfile:
        out_path = args.file
    else:
        dir_name = os.path.dirname(args.cnv_data)
        base_name = os.path.basename(args.cnv_data)
        prefix = base_name.split('.')[0]
        out_file = "{}.{}.CNV_plottable.tsv".format(prefix, args.package)
        out_path = os.path.join(dir_name, out_file)
    # save the data
    df.to_csv(out_path, sep='\t', index=False)