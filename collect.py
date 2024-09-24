#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from getpass import getpass
import aiohttp
import os
import argparse
import textwrap
import asyncio
import schedule
import json

# Configuration des proxies pour les requêtes HTTP et HTTPS
proxies = {'http': 'http://pxy-http-srv.serv.cdc.fr:8080', 'https': 'http://pxy-http-srv.serv.cdc.fr:8080'}

class Gamera:
    """
    Classe pour interagir avec l'API Gamera.
    
    Cette classe fournit des méthodes pour récupérer tous les projets
    depuis l'API Gamera et les sauvegarder localement.

    Attributes:
        username (str): Nom d'utilisateur pour l'authentification.
        password (str): Mot de passe pour l'authentification.
        gamera_api (str): URL de base de l'API Gamera.
        session (aiohttp.ClientSession): Session HTTP pour les requêtes (initialisée à None).
    """

    def __init__(self, username, password):
        """
        Initialise une instance de la classe Gamera.

        Args:
            username (str): Nom d'utilisateur pour l'authentification.
            password (str): Mot de passe pour l'authentification.
        """
        self.username = username
        self.password = password
        self.gamera_api = "https://gamera.serv.cdc.fr/squash/api/rest/latest/"
        self.session = None

    async def fetch(self, url):
        """
        Effectue une requête GET asynchrone vers l'URL spécifiée.

        Args:
            url (str): L'URL à interroger.

        Returns:
            dict: Les données JSON retournées par l'API.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=aiohttp.BasicAuth(self.username, self.password), proxy=proxies['http']) as response:
                return await response.json()

    async def get_list_all_projects(self):
        """
        Récupère la liste de tous les projets depuis l'API Gamera.

        Returns:
            dict: Les données JSON contenant tous les projets.
        """
        url = f"{self.gamera_api}projects?size=10000000000"
        return await self.fetch(url)

    async def update_projects(self):
        """
        Met à jour la liste des projets et les sauvegarde dans un fichier.

        Cette méthode récupère tous les projets, les sauvegarde dans un fichier JSON,
        et affiche un message de confirmation avec l'horodatage.
        """
        projects = await self.get_list_all_projects()
        self.save_to_file('projects.json', projects)
        print(f'Projects updated successfully at {time.strftime("%Y-%m-%d %H:%M:%S")}')

    def save_to_file(self, filename, data):
        """
        Sauvegarde les données dans un fichier JSON.

        Args:
            filename (str): Le nom du fichier dans lequel sauvegarder les données.
            data (dict): Les données à sauvegarder.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


class Scheduler:
    """
    Classe pour planifier et exécuter des mises à jour périodiques.

    Attributes:
        fetcher (Gamera): Instance de la classe Gamera pour effectuer les mises à jour.
        interval_hours (int): Intervalle en heures entre chaque mise à jour.
    """

    def __init__(self, fetcher, interval_hours):
        """
        Initialise une instance de la classe Scheduler.

        Args:
            fetcher (Gamera): Instance de la classe Gamera pour effectuer les mises à jour.
            interval_hours (int): Intervalle en heures entre chaque mise à jour.
        """
        self.fetcher = fetcher
        self.interval_hours = interval_hours

    def start(self):
        """
        Démarre le planificateur.

        Cette méthode configure la planification des mises à jour et exécute
        une première mise à jour immédiatement. Ensuite, elle entre dans une
        boucle infinie pour exécuter les tâches planifiées.
        """
        schedule.every(self.interval_hours).hours.do(lambda: asyncio.run(self.fetcher.update_projects()))
        asyncio.run(self.fetcher.update_projects())

        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    """
    Fonction principale du script.

    Cette fonction configure l'analyseur d'arguments, crée une instance de Gamera,
    initialise le planificateur et démarre le processus de mise à jour périodique.
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent('''\
        A script to retrieve and update the list of projects from Gamera API.
        ---------------------------------------------------------------------------
            Make sure to have the right username and password.
            The script updates the list of projects every 2 hours.
        '''))

    parser.add_argument("-u", dest="username", required=True, help="Specify the username")
    args = parser.parse_args()

    project = Gamera(args.username, getpass("Enter your password: "))
    scheduler = Scheduler(project, 2)
    scheduler.start()


if __name__ == "__main__":
    main()