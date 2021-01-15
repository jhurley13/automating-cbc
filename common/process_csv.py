"""
Convert a "raw" CSV file with CommonName,Total fields to a personal_checklist dataframe
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from utilities_cbc import read_excel_or_csv_path
# Local imports
from ebird_extras import EBirdExtra
from ebird_visits import transform_checklist_details
from local_translation_context import LocalTranslationContext
from taxonomy import Taxonomy
from text_transform import clean_common_names


# local_translation_context = LocalTranslationContext(None, None)
# bob_hirt_path = inputs_merge_path / 'CACR-bob-hirt.csv'
# checklist = read_excel_or_csv_path(bob_hirt_path)


# Now for Bob Hirt
def raw_csv_to_checklist(fpath: Path,
                         taxonomy: Taxonomy,
                         local_translation_context: LocalTranslationContext,
                         observer_name: str,
                         xdates: List[str],
                         latitude: Optional[float],
                         longitude: Optional[float]
                         ) -> pd.DataFrame:
    """

    :param fpath:
    :param taxonomy:
    :param local_translation_context:
    :param observer_name:
    :param observation_date: e.g. '2020-12-26'
    :param circle_code:
    :param sector_name:
    :param latitude:
    :param longitude:
    :return:
    """
    csvdf = read_excel_or_csv_path(fpath)
    df = csv_dataframe_to_checklist(csvdf, taxonomy, local_translation_context,
                                    observer_name,
                                    xdates
                                    )
    if df is None:
        print(f'File {fpath} is not a valid species data file')
    return df


def csv_dataframe_to_checklist(checklist: pd.DataFrame,
                               taxonomy: Taxonomy,
                               local_translation_context: LocalTranslationContext,
                               observer_name: str,
                               xdates: List[str]
                               ) -> Optional[pd.DataFrame]:
    # Use column names from eBird and let them be fixed by transform_checklist_details

    if set(checklist.columns) & {'CommonName', 'Total'} == set():
        return None

    cleaned_common_names = clean_common_names(checklist.CommonName,
                                              taxonomy, local_translation_context)
    checklist.CommonName = cleaned_common_names

    # This will get switched back by transform_checklist_details
    checklist.rename(columns={'Total': 'howManyStr'}, inplace=True)
    xdtypes = {'CommonName': str, 'howManyStr': int}
    checklist = checklist.astype(dtype=xdtypes)

    checklist['speciesCode'] = [taxonomy.find_species6_ebird(cn) for cn in checklist.CommonName]
    checklist['locId'] = 'L5551212'
    checklist['subId'] = 'S5551212'
    checklist['groupId'] = ''
    checklist['durationHrs'] = 0.5
    checklist['effortDistanceKm'] = 0.1
    checklist['effortDistanceEnteredUnit'] = 'mi'
    # 'obsDt' needs dates in this form '26 Dec 2020'
    obsdt = datetime.strptime(xdates[0], '%Y-%m-%d').strftime('%d %b %Y')
    checklist['obsDt'] = f'{obsdt} 12:01'

    checklist['userDisplayName'] = observer_name

    # Clean up
    checklist = transform_checklist_details(checklist, taxonomy)

    return checklist


def subids_to_checklist(subids: List[str],
                        ebird_extra: EBirdExtra,
                        taxonomy: Taxonomy,
                        observer_name: str,
                        xdates: List[str]
                        ) -> pd.DataFrame:
    """
    Only handles one date right now
    :param subids:
    :param observation_date:  e.g. '2020-12-26'
    :return:
    """
    # We jump through this hoop to take advantage of caching of eBird data
    # The only fields of visits that get_details_for_dates uses are subId and obsDt
    xvisits = pd.DataFrame()
    xvisits['subId'] = subids
    # 'obsDt' needs dates in this form '26 Dec 2020'
    obsdt = datetime.strptime(xdates[0], '%Y-%m-%d').strftime('%d %b %Y')
    xvisits['obsDt'] = obsdt  # e.g. '26 Dec 2020'

    subids_by_date = {xdates[0]: subids}
    details = ebird_extra.get_details_for_dates(subids_by_date, xdates)

    checklist = transform_checklist_details(details, taxonomy)
    checklist['Name'] = observer_name

    return checklist

# cols_to_keep = ['locId', 'subId', 'userDisplayName', 'groupId',
#                     'speciesCode', 'obsDt', 'howManyStr']
