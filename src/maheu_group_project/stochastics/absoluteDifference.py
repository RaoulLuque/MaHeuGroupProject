import pandas as pd
import os

def test():
    print("test successful")

def allDiffs():
    import pandas as pd

    # Planned Capacity einlesen
    planned_df = pd.read_csv('data\\CaseMaHeu25_01\\planned_capacity_data.csv', sep=';')

    # Schleife über die 10 Realised-Dateien
    for i in range(1, 11):
        suffix = f"{i:03}"  # '001', '002', ..., '010'
        realised_file = f"data\\CaseMaHeu25_01\\realised_capacity_data_{suffix}.csv"

        realised_df = pd.read_csv(realised_file, sep=';')
        new_col_name = f'CapacityAbsDiff{suffix}'
        planned_df[new_col_name] = None

        # Vergleiche zeilenweise
        for idx, row in planned_df.iterrows():
            path = row['PathSegmentCode']
            dep = row['Departure']
            arr = row['Arrival']

            # Passende Zeile im Realised-DataFrame suchen
            match = realised_df[
                (realised_df['PathSegmentCode'] == path) &
                (realised_df['Departure'] == dep) &
                (realised_df['Arrival'] == arr)
            ]

            if not match.empty:
                realised_capacity = match.iloc[0]['Capacity']
                planned_capacity = row['Capacity']
                diff = realised_capacity - planned_capacity
                planned_df.at[idx, new_col_name] = diff
            else:
                planned_df.at[idx, new_col_name] = None  # Oder 0, je nach Bedarf
                
    # save the DataFrame with all differences to a new CSV file in the same file as stochastics
    output_path = 'src\\maheu_group_project\\stochastics\\output\\csvFiles\\CaseMaHeu25_01\\planned_with_all_diffs.csv'
    planned_df.to_csv(output_path, sep=';', index=False)
    print(f"Neue CSV wurde gespeichert unter: {output_path}")

def cDiff():
    import pandas as pd

    # CSV-Dateien einlesen (mit korrektem Trenner)
    planned_df = pd.read_csv('data\\CaseMaHeu25_01\\planned_capacity_data.csv', sep=';')
    realised_df = pd.read_csv('data\\CaseMaHeu25_01\\realised_capacity_data_001.csv', sep=';')

    # Neue Spalte initialisieren
    planned_df['CapacityAbsDiff001'] = None

    # Durch jede Zeile in planned_df iterieren
    for i, row in planned_df.iterrows():
        path = row['PathSegmentCode']
        dep = row['Departure']
        arr = row['Arrival']

        # Finde passende Zeile in realised_df
        match = realised_df[
            (realised_df['PathSegmentCode'] == path) &
            (realised_df['Departure'] == dep) &
            (realised_df['Arrival'] == arr)
        ]

        if not match.empty:
            realised_capacity = match.iloc[0]['Capacity']
            planned_capacity = row['Capacity']
            diff = abs(planned_capacity - realised_capacity)
            planned_df.at[i, 'CapacityAbsDiff001'] = diff
        else:
            # Kein passender Eintrag gefunden – ggf. NaN oder 0
            planned_df.at[i, 'CapacityAbsDiff001'] = None
            print('No match found for row:', row)

    # Neue CSV speichern
    planned_df.to_csv('CaseMaHeu25_01_with_CapacityAbsDiff001.csv', sep=';', index=False)


def absDif():
    # Dateien einlesen
    planned_df = pd.read_csv('data\\CaseMaHeu25_01\\planned_capacity_data.csv', sep=';')
    realised_df = pd.read_csv('data\\CaseMaHeu25_01\\realised_capacity_data_001.csv', sep=';')

    print(len(planned_df))
    print(len(realised_df))


    # calculate the absolute difference of Capacity values for each row of planned_df and realised_df
    capdif_df = pd.DataFrame({
        'CapDiff': planned_df['Capacity'].values - realised_df['Capacity'].values
    })




    # Neue CSV speichern
    output_path = 'output/csvFiles/absolute_Differences_Case01_realised001.csv'
    capdif_df.to_csv(output_path, index=False)

    print(f"Neue CSV wurde gespeichert unter: {output_path}")

def allDiffs2():
    import pandas as pd
    import os

    for case_num in range(1, 5):
        case_str = f"CaseMaHeu25_{case_num:02}" # Formating for CaseMaHeu25_01, CaseMaHeu25_02, etc.
        planned_path = f"data\\{case_str}\\planned_capacity_data.csv"
        planned_df = pd.read_csv(planned_path, sep=';')

        for i in range(1, 11):
            suffix = f"{i:03}"
            realised_file = f"data\\{case_str}\\realised_capacity_data_{suffix}.csv"
            realised_df = pd.read_csv(realised_file, sep=';')
            new_col_name = f'CapacityAbsDiff{suffix}'
            planned_df[new_col_name] = None

            for idx, row in planned_df.iterrows():
                path = row['PathSegmentCode']
                dep = row['Departure']
                arr = row['Arrival']
                match = realised_df[
                    (realised_df['PathSegmentCode'] == path) &
                    (realised_df['Departure'] == dep) &
                    (realised_df['Arrival'] == arr)
                ]
                if not match.empty:
                    realised_capacity = match.iloc[0]['Capacity']
                    planned_capacity = row['Capacity']
                    diff = realised_capacity - planned_capacity
                    planned_df.at[idx, new_col_name] = diff
                else:
                    planned_df.at[idx, new_col_name] = None

        output_dir = os.path.join('src', 'maheu_group_project', 'stochastics', 'output', 'csvFiles', 'absoluteDifferences', case_str)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'planned_with_all_diffs_Case0{case_num}.csv')
        planned_df.to_csv(output_path, sep=';', index=False)
        print(f"Neue CSV wurde gespeichert unter: {output_path}")

# This function calculates the standard deviation of relative differences for each row in the planned capacity data, comparing it with multiple realised capacity files.
# For each case, it computes the relative capacity differences and calculates the respective standard deviation and mean over all values provided by the realised data.
# It saves the results in a new CSV file, including an adjusted capacity column based on the mean and standard deviation of the relative differences.
def standardabweichung():
    import pandas as pd
    import os
    import numpy as np

    for case_num in range(1, 4):
        case_str = f"CaseMaHeu25_{case_num:02}" # Formating for CaseMaHeu25_01, CaseMaHeu25_02, etc.
        planned_path = f"data\\{case_str}\\planned_capacity_data.csv"
        planned_df = pd.read_csv(planned_path, sep=';')

        normalized_values = []

        for i in range(1, 11):
            suffix = f"{i:03}"
            realised_file = f"data\\{case_str}\\realised_capacity_data_{suffix}.csv"
            realised_df = pd.read_csv(realised_file, sep=';')
            new_col_name = f'CapacityAbsDiff{suffix}'
            planned_df[new_col_name] = None

            for idx, row in planned_df.iterrows():
                path = row['PathSegmentCode']
                dep = row['Departure']
                arr = row['Arrival']
                match = realised_df[
                    (realised_df['PathSegmentCode'] == path) &
                    (realised_df['Departure'] == dep) &
                    (realised_df['Arrival'] == arr)
                ]
                if not match.empty:
                    realised_capacity = match.iloc[0]['Capacity']
                    planned_capacity = row['Capacity']
                    frac = realised_capacity / planned_capacity if planned_capacity != 0 else None
                    normalized_values.append(frac)
                    planned_df.at[idx, new_col_name] = frac
                else:
                    planned_df.at[idx, new_col_name] = None
        mean_normalized = np.mean(normalized_values)
        std_relative = np.std(normalized_values, ddof=1)  # ddof=1 for sample standard deviation

        # Add the mean and standard deviation as new columns
        planned_df['MeanNormalized'] = mean_normalized
        planned_df['StdRelative'] = std_relative
        planned_df['StdAbsolute'] = planned_df['StdRelative'] * planned_df['Capacity']
        # add adjusted capacity to plan with
        planned_df['AdjustedCapacity'] = np.minimum(planned_df['Capacity'], mean_normalized * planned_df['Capacity'] - planned_df['StdAbsolute'])

        output_dir = os.path.join('src', 'maheu_group_project', 'stochastics', 'output', 'csvFiles', 'relativeDifferences_perCase')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'planned_with_normalized_differences_Case0{case_num}.csv')
        planned_df.to_csv(output_path, sep=';', index=False)
        print(f"Neue CSV wurde gespeichert unter: {output_path}")

# This function calculates the standard deviation of relative differences for each row in the planned capacity data, comparing it with multiple realised capacity files.
# It computes the relative differences, calculates the standard deviation and mean for each row, and saves the results in a new CSV file.
# It also adds an adjusted capacity column based on the mean and standard deviation of the relative differences.
def standardabweichung_perDay():
    import pandas as pd
    import os
    import numpy as np

    for case_num in range(1, 4):
        case_str = f"CaseMaHeu25_{case_num:02}"
        planned_path = f"data\\{case_str}\\planned_capacity_data.csv"
        planned_df = pd.read_csv(planned_path, sep=';')

        rel_diff_cols = [f'CapacityRelDiff{str(i).zfill(3)}' for i in range(1, 11)]
        std_devs = []
        means = []

        # For each row, collect relative diffs for all 10 realised files
        for idx, row in planned_df.iterrows():
            rel_diffs = []
            for i in range(1, 11):
                suffix = f"{i:03}"
                realised_file = f"data\\{case_str}\\realised_capacity_data_{suffix}.csv"
                realised_df = pd.read_csv(realised_file, sep=';')
                match = realised_df[
                    (realised_df['PathSegmentCode'] == row['PathSegmentCode']) &
                    (realised_df['Departure'] == row['Departure']) &
                    (realised_df['Arrival'] == row['Arrival'])
                ]
                col_name = f'CapacityRelDiff{suffix}'
                if not match.empty:
                    realised_capacity = match.iloc[0]['Capacity']
                    planned_capacity = row['Capacity']
                    frac = realised_capacity / planned_capacity if planned_capacity != 0 else None
                    planned_df.at[idx, col_name] = frac
                    rel_diffs.append(frac)
                else:
                    planned_df.at[idx, col_name] = None
            # Calculate std deviation and mean for this row (ignoring None)
            rel_diffs_clean = [v for v in rel_diffs if v is not None]
            std_val = np.std(rel_diffs_clean, ddof=1) if len(rel_diffs_clean) > 1 else None
            mean_val = np.mean(rel_diffs_clean) if len(rel_diffs_clean) > 0 else None
            std_devs.append(std_val)
            means.append(mean_val)
        # Insert std deviation and mean columns after last rel diff column
        last_col = rel_diff_cols[-1]
        insert_at = planned_df.columns.get_loc(last_col) + 1
        planned_df.insert(insert_at, 'MeanRelDiff', means)
        planned_df.insert(insert_at + 1, 'StdRelDiff', std_devs)

        # add adjusted capacity to plan with
        planned_df['AdjustedCapacity'] = np.minimum(planned_df['Capacity'], (planned_df['MeanRelDiff'] - planned_df['StdRelDiff']) * planned_df['Capacity'])

        output_dir = os.path.join('src', 'maheu_group_project', 'stochastics', 'output', 'csvFiles', 'relativeDifferences')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'planned_with_relative_differences_Case0{case_num}.csv')
        planned_df.to_csv(output_path, sep=';', index=False)
        print(f"Neue CSV wurde gespeichert unter: {output_path}")