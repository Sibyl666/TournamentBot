import gspread
from oauth2client.service_account import ServiceAccountCredentials

json_path = "osutournamentdiscordjoincheck-84f8d6e67c81.json"

def get_credentials():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    return gspread.authorize(credentials)



def create_new_qualifier_sheet(lobby_name, referee, teams):

    gs = get_credentials()    

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


def create_new_match_sheet(match_name, match_data, maps):

    gs = get_credentials()

    url = "https://docs.google.com/spreadsheets/d/1Xy2MD07WPixSqJ62RRm6KfgeujbYKjpn7PnQ45Cuaw0/"
    ss = gs.open_by_url(url)
    
    coppied_sheet = ss.worksheet("Ref Sheet Taskak")
    duplicated_sheet = ss.duplicate_sheet(coppied_sheet.id, insert_sheet_index=len(ss.worksheets()), new_sheet_name=f"Lobi {match_name} - {match_data['referee']['name']} - Hakem Sheet")
    update_cells = []

    setup_cells = duplicated_sheet.range("C3:C5")
    setup_cells[0].value = match_name
    setup_cells[1].value = match_data["pool"]
    setup_cells[2].value = match_data["referee"]["name"]
    duplicated_sheet.update_cells(setup_cells, value_input_option='USER_ENTERED')

    if match_data["streamer"] is not None:
        refere_cell = duplicated_sheet.acell("B10")
        refere_cell.value = match_data["streamer"]["osu_name"]
        update_cells = [refere_cell]
    
    range_notations = ["E4:E6", "K4:K6"]
    for index, (team_name, team_data) in enumerate(match_data["teams"].items()):
        team_cells = duplicated_sheet.range(range_notations[index])
        team_cells[0].value = team_name
        team_cells[1].value = team_data["user_1_name"]
        team_cells[2].value = team_data["user_2_name"]
        update_cells += team_cells

    beatmap_cells = duplicated_sheet.range("S2:S20")
    id_cells = duplicated_sheet.range("T2:T20")
    for index, (map_id, map_data) in enumerate(maps.items()):
        beatmap_cells[index].value = map_data["map_string"]
        id_cells[index].value = f"!mp map {map_id}"

    update_cells += beatmap_cells + id_cells

    duplicated_sheet.update_cells(update_cells, value_input_option='USER_ENTERED')

    return (url + "edit#gid=" + str(duplicated_sheet.id), duplicated_sheet.id)

def get_sheet_data(sheet_id):

    gs = get_credentials()  

    url = "https://docs.google.com/spreadsheets/d/1Xy2MD07WPixSqJ62RRm6KfgeujbYKjpn7PnQ45Cuaw0/"
    ss = gs.open_by_url(url)

    current_sheet = None
    for worksheet in ss.worksheets():
        if worksheet.id == sheet_id:
            current_sheet = worksheet

    if current_sheet == None:
        raise KeyError("Sheet with the id could not found")

    mp_link = current_sheet.acell("B8").value

    blue_team_name = current_sheet.acell("E4").value
    red_team_name = current_sheet.acell("K4").value

    teams = {blue_team_name:{}, red_team_name:{}}

    teams[blue_team_name]["score"] = current_sheet.acell("H2").value
    teams[red_team_name]["score"] =  current_sheet.acell("J2").value

    teams[blue_team_name]["roll"] = current_sheet.acell("H9").value
    teams[red_team_name]["roll"] =  current_sheet.acell("J9").value
    
    blue_bans = current_sheet.range("E9:E10")
    blue_bans = list(map(lambda x: x.value[:3], blue_bans))
    teams[blue_team_name]["bans"] = blue_bans

    red_bans = current_sheet.range("K9:K10")
    red_bans = list(map(lambda x: x.value[:3], red_bans))
    teams[red_team_name]["bans"] = red_bans

    return (mp_link, teams)