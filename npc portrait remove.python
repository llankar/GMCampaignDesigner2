#!/usr/bin/env python3
import json
import os

# Liste des noms de fichiers de portraits autorisés
allowed_portraits = {
    "Abyssal_Herald_portrait.png",
    "Abyssal_Hound_portrait.png",
    "Aiden_Carver_portrait.png",
    "Alessandra_'Sandy'_Marino_portrait.png",
    "Anita_Patel_portrait.png",
    "Antonia_Rosetti_portrait.png",
    "Arcane_Geologist_and_Paranormal_Engineer_portrait.png",
    "Archivist_Yewthorn_portrait.png",
    "Archivist_Yoko_Tamura_portrait.png",
    "Bishop_Tallow_portrait.png",
    "Blacksmith_Gavin_Hurst_portrait.png",
    "Bramble_portrait.png",
    "Captain_Dreth_portrait.png",
    "Captain_Sofia_Domingez_portrait.png",
    "Carter_Finch_portrait.png",
    "Chained_Horror_portrait.png",
    "Chainmaker_Aldous_portrait.png",
    "Chaos_Bringer_portrait.png",
    "Cora_Dewdrop_portrait.png",
    "Corrupt_Spawn_portrait.png",
    "Demon_Grishkar_portrait.png",
    "Demon_Prince_Velkar_portrait.png",
    "Detective_Irene_Vale_portrait.png",
    "Detective_Marla_Reyes_portrait.png",
    "Detective_Sam_Brody_portrait.png",
    "Detective_Sofia_Vasquez_portrait.png",
    "Dexter_'Dex'_Thompson_portrait.png",
    "Diego_'D'_Alvarez_portrait.png",
    "Dr._Elise_Navarro_portrait.png",
    "Dr._Nora_Ellis_portrait.png",
    "Echo_Wraith_portrait.png",
    "Elder_Tidecaller_Orsk_portrait.png",
    "Eldritch_Titan_portrait.png",
    "Eleanor_Drake_portrait.png",
    "Emily_Green_portrait.png",
    "Emmeline_Vail_(Ghost)_portrait.png",
    "Ettelwin_Crook_portrait.png",
    "Evelyn_'Evie'_Dawson_portrait.png",
    "Eye_of_Despair_portrait.png",
    "Fae_Spirit_of_Spiteful_Love_portrait.png",
    "Father_Michael_Evans_portrait.png",
    "Glimmerjack_the_Bartender_portrait.png",
    "Gloria_'Glo'_Richmond_portrait.png",
    "Griselda_the_Hag_portrait.png",
    "Harbinger_of_the_Void_portrait.png",
    "Jenna_Moreno_portrait.png",
    "Joe_Callahan_portrait.png",
    "Julia_Foster_portrait.png",
    "King_Corb_portrait.png",
    "Knight_Armand_St._Croix_portrait.png",
    "Knight_Captain_Mariel_Brightwind_portrait.png",
    "Kraig_Stoneback_portrait.png",
    "Lady_Elaris_portrait.png",
    "Lady_Morvena_portrait.png",
    "Lana_Brooks_portrait.png",
    "Liam_Raith_portrait.png",
    "Lily_and_Rose_Winter_portrait.png",
    "Liora_Brightflame_portrait.png",
    "Lirak_the_Harvester_portrait.png",
    "Lord_Balor_portrait.png",
    "Lord_Jonathan_Blackwood_portrait.png",
    "Lord_Na'thraal_portrait.png",
    "Lucinda_Raith_portrait.png",
    "Marcy_Calhoun_portrait.png",
    "Meera_Kline_portrait.png",
    "Mikhail_Azarov_portrait.png",
    "Milo_Trask_portrait.png",
    "Mireana_the_Weaver_portrait.png",
    "Morran_the_Ice-Touched_portrait.png",
    "Nicodemus_Archleone_portrait.png",
    "Nightmare_Ripper_portrait.png",
    "Nox_portrait.png",
    "Oblivion_Warden_portrait.png",
    "Orcus_Darkhoof_portrait.png",
    "Pastor_Caleb_North_portrait.png",
    "Professor_Henry_Caldwell_portrait.png",
    "Puck_portrait.png",
    "Queen_Briarheart_portrait.png",
    "Raymond_'Ray'_Sanchez_portrait.png",
    "Rift_Stalker_portrait.png",
    "Rory_'Frostbite'_Mallory_portrait.png",
    "Rusk_the_Reclaimer_portrait.png",
    "Samira_Khan_portrait.png",
    "Sarai_Givens_portrait.png",
    "Sergeant_Morloch_portrait.png",
    "Shattered_Apparition_portrait.png",
    "Sir_Alden_portrait.png",
    "Sir_Elijah_Castor_portrait.png",
    "Sister_Maria_Bell_portrait.png",
    "Sorceress_Marina_portrait.png",
    "Sylvia_Heartswell_portrait.png",
    "test.txt",
    "Thane_Coldfingers_portrait.png",
    "The_Abyss_Choir_portrait.png",
    "The_Blood_Hag_Mirskaya_portrait.png",
    "The_Bound_Jester_portrait.png",
    "The_Corruptor_portrait.png",
    "The_Ferruling_Host_portrait.png",
    "The_Hollow_Prince_portrait.png",
    "The_Voice_Beneath_the_Ice_portrait.png",
    "The_Weeping_Angel_portrait.png",
    "Thorne_Greenheart_portrait.png",
    "Tommy_Greer_portrait.png",
    "Veil_Shifter_portrait.png",
    "Velna_of_the_Thousand_Blooms_portrait.png",
    "Vessara_the_Whisper_portrait.png",
    "Vladislav_'Vlad'_Sokolov_portrait.png",
    "Voidling__portrait.png",
    "Warden_Ezekiel_Cross_portrait.png",
    "Warden_Lysander_Black_portrait.png",
    "Whispering_Shadow_portrait.png",
    "Willa_Nkomo_portrait.png",
    "Wyld_Healer_Brialyn_portrait.png",
    "Wyld_Huntress_Seline_portrait.png",
    "Wyrshae,_the_Hollow_Whisperer_portrait.png"
}

def nettoyer_portraits(data):
    """
    Pour chaque objet du JSON, si le champ "Portrait" existe,
    on vérifie si le nom du fichier (basename) figure dans la liste autorisée.
    Sinon, on supprime ce champ.
    """
    for obj in data:
        portrait = obj.get("Portrait")
        if portrait:
            # Extraction du nom de fichier (en tenant compte des séparateurs de chemin)
            filename = os.path.basename(portrait)
            if filename not in allowed_portraits:
                # Supprimer le champ "Portrait" si le fichier n'est pas autorisé
                obj.pop("Portrait")
    return data

def main():
    # Nom du fichier JSON d'entrée et sortie (à adapter selon vos besoins)
    input_file = "npcs.json"
    output_file = "npcs_cleaned_data.json"
    
    # Charger le JSON
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Nettoyer la liste des portraits
    data_cleaned = nettoyer_portraits(data)
    
    # Sauvegarder le JSON nettoyé
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data_cleaned, f, indent=2, ensure_ascii=False)
    
    print(f"Nettoyage terminé. Le fichier nettoyé a été enregistré dans '{output_file}'.")

if __name__ == "__main__":
    main()
