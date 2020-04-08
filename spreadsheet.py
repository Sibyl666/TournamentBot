import gspread
from oauth2client.service_account import ServiceAccountCredentials

from database import read_lobby_db

json_path = "osutournamentdiscordjoincheck-84f8d6e67c81.json"

def create_new_qualifier_sheet(lobby_name, referee, teams):

    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    gs = gspread.authorize(credentials)

    url = "https://docs.google.com/spreadsheets/d/1Xy2MD07WPixSqJ62RRm6KfgeujbYKjpn7PnQ45Cuaw0/"
    ss = gs.open_by_url(url)
    
    coppied_sheet = ss.worksheet("Sıralama Sheet Taslak")
    duplicated_sheet = ss.duplicate_sheet(coppied_sheet.id, insert_sheet_index=len(ss.worksheets()), new_sheet_name=f"Lobi {lobby_name} - {referee} - Sıralama Sheet")
    team_cells = duplicated_sheet.range(f"E4:E24")

    for index, (team_name, team_data) in enumerate(teams.items()):
        
        team_cells[index*3].value = team_name
        team_cells[index*3+1].value = team_data[0][1]
        team_cells[index*3+2].value = team_data[1][1]

    setup_cells = duplicated_sheet.range(f"C3:C5")
    setup_cells[0].value = lobby_name
    setup_cells[2].value = referee

    update_cells = setup_cells + team_cells
    duplicated_sheet.update_cells(update_cells, value_input_option='USER_ENTERED')

    return url + "edit#gid=" + str(duplicated_sheet.id)

