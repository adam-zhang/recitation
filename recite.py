#!/usr/bin/env python3
import requests
import json
import time
from datetime import datetime, timedelta
import pickle
import os
from typing import List, Dict, Optional
import argparse

class WordMemorySystem:
    def __init__(self, data_file="word_memory.pkl"):
        """
        Initialize word memory system
        """
        self.data_file = data_file
        self.words = self.load_data()

        # Ebbinghaus review intervals (in days)
        self.ebbinghaus_intervals = [0, 1, 2, 6, 31]

    def load_data(self) -> Dict:
        """
        Load saved word data
        """
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                return pickle.load(f)
        return {}

    def save_data(self):
        """
        Save word data to file
        """
        with open(self.data_file, 'wb') as f:
            pickle.dump(self.words, f)

    def fetch_definition_from_webster(self, word: str) -> Dict:
        """
        Fetch word definition from Merriam-Webster API
        Note: API key required, this is example code
        """
        # Using a free alternative API
        try:
            # Method 1: Use Dictionary API (free, no API key needed)
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    word_data = data[0]

                    definitions = []
                    examples = []

                    for meaning in word_data.get('meanings', []):
                        for definition in meaning.get('definitions', []):
                            definitions.append(definition.get('definition', ''))
                            if 'example' in definition:
                                examples.append(definition.get('example'))

                    return {
                            'word': word,
                            'meanings': definitions[:3],  # Take first 3 definitions
                            'examples': examples[:2],      # Take first 2 examples
                            'phonetic': word_data.get('phonetic', ''),
                            'source': 'dictionaryapi.dev'
                            }
        except Exception as e:
            print(f"Failed to fetch from dictionary API: {e}")

        # Alternative method: Use Datamuse API
        try:
            url = f"https://api.datamuse.com/words?sp={word}&md=d&max=1"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                            'word': word,
                            'meanings': [data[0].get('defs', ['No definition found'])[0] if 'defs' in data[0] else 'No definition found'],
                            'examples': [],
                            'phonetic': '',
                            'source': 'datamuse.com'
                            }
        except Exception as e:
            print(f"Failed to fetch from Datamuse: {e}")

        return None

    def add_word(self, word: str, custom_definition: str = None):
        """
        Add new word to memory system
        """
        word_lower = word.lower().strip()

        if word_lower in self.words:
            print(f"Word '{word}' is already in the memory list!")
            return False

        print(f"\nLooking up word: {word}")

        # Fetch word definition
        if custom_definition:
            word_info = {
                    'word': word,
                    'meanings': [custom_definition],
                    'examples': [],
                    'phonetic': '',
                    'source': 'custom'
                    }
        else:
            word_info = self.fetch_definition_from_webster(word_lower)

            if not word_info:
                print("Unable to fetch definition from online resources.")
                use_custom = input("Enter definition manually? (y/n): ").lower()
                if use_custom == 'y':
                    custom_def = input("Enter definition: ")
                    word_info = {
                            'word': word,
                            'meanings': [custom_def],
                            'examples': [],
                            'phonetic': '',
                            'source': 'manual'
                            }
                else:
                    return False

        # Create memory record
        now = datetime.now()
        review_dates = [now + timedelta(days=interval) for interval in self.ebbinghaus_intervals]

        self.words[word_lower] = {
                'info': word_info,
                'added_date': now,
                'review_dates': review_dates,
                'last_reviewed': None,
                'review_count': 0,
                'mastery_level': 0,  # 0-4, indicates mastery level
                'next_review': review_dates[1] if len(review_dates) > 1 else now,  # First review is tomorrow
                }

        self.save_data()

        # Display word information
        self.display_word_info(word_info)
        print(f"\n✓ Word '{word}' added to memory system!")
        print(f"  First review: {review_dates[1].strftime('%Y-%m-%d %H:%M')}")

        return True

    def display_word_info(self, word_info: Dict):
        """
        Display word information
        """
        print("\n" + "="*50)
        print(f"Word: {word_info['word']}")

        if word_info.get('phonetic'):
            print(f"Phonetic: /{word_info['phonetic']}/")

        print("\nDefinitions:")
        for i, meaning in enumerate(word_info['meanings'], 1):
            print(f"  {i}. {meaning}")

        if word_info.get('examples'):
            print("\nExamples:")
            for i, example in enumerate(word_info['examples'], 1):
                print(f"  {i}. {example}")

        if word_info.get('source'):
            print(f"\nData source: {word_info['source']}")

        print("="*50)

    def get_words_for_review(self) -> List[str]:
        """
        Get words that need review
        """
        now = datetime.now()
        words_to_review = []

        for word, data in self.words.items():
            if data['next_review'] <= now:
                words_to_review.append(word)

        return words_to_review

    def review_word(self, word: str):
        """
        Review a word
        """
        if word not in self.words:
            print(f"Word '{word}' not found!")
            return False

        data = self.words[word]

        # Display word information
        self.display_word_info(data['info'])

        # Get user feedback
        print("\nRate your memory:")
        print("1. Completely forgot")
        print("2. Vague memory")
        print("3. Remember with effort")
        print("4. Remember clearly")
        print("5. Fully mastered")

        while True:
            try:
                mastery = int(input("\nSelect (1-5): "))
                if 1 <= mastery <= 5:
                    break
                print("Please enter a number between 1-5!")
            except ValueError:
                print("Please enter a valid number!")

        # Update memory data
        data['last_reviewed'] = datetime.now()
        data['review_count'] += 1
        data['mastery_level'] = mastery - 1  # Convert to 0-4 mastery level

        # Adjust next review time based on mastery
        if mastery >= 4:  # Good memory
            # Find next review interval
            current_index = min(data['review_count'], len(self.ebbinghaus_intervals) - 1)
            if current_index < len(self.ebbinghaus_intervals) - 1:
                next_interval = self.ebbinghaus_intervals[current_index + 1]
                data['next_review'] = datetime.now() + timedelta(days=next_interval)
            else:
                # Completed all Ebbinghaus reviews
                data['next_review'] = datetime.now() + timedelta(days=365)  # After 1 year
        elif mastery >= 2:  # Partial memory
            data['next_review'] = datetime.now() + timedelta(hours=12)  # After 12 hours
        else:  # Forgot
            data['next_review'] = datetime.now() + timedelta(hours=1)  # After 1 hour

        self.save_data()

        next_review_str = data['next_review'].strftime('%Y-%m-%d %H:%M')
        print(f"\n✓ Review completed! Next review: {next_review_str}")

        return True

    def show_review_schedule(self, word: str = None):
        """
        Display review schedule
        """
        print("\n" + "="*60)
        print("Ebbinghaus Forgetting Curve Review Schedule")
        print("="*60)

        if word:
            if word in self.words:
                data = self.words[word]
                self._display_word_schedule(word, data)
            else:
                print(f"Word '{word}' not found!")
        else:
            # Display schedule for all words
            if not self.words:
                print("No words in memory system.")
                return

            # Sort by next review time
            sorted_words = sorted(
                    self.words.items(),
                    key=lambda x: x[1]['next_review']
                    )

            print(f"{'Word':<15} {'Mastery':<10} {'Reviews':<8} {'Next Review':<20}")
            print("-" * 60)

            for word, data in sorted_words:
                mastery_str = "★" * (data['mastery_level'] + 1) + "☆" * (4 - data['mastery_level'])
                next_review = data['next_review'].strftime('%m-%d %H:%M')

                # Mark as overdue if past due
                if data['next_review'] < datetime.now():
                    next_review = f"⚠ {next_review}"

                print(f"{word:<15} {mastery_str:<10} {data['review_count']:<8} {next_review:<20}")

    def _display_word_schedule(self, word: str, data: Dict):
        """
        Display detailed review schedule for a single word
        """
        word_info = data['info']
        print(f"\nWord: {word}")
        print(f"Added: {data['added_date'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Reviews: {data['review_count']}")
        print(f"Mastery: {'★' * (data['mastery_level'] + 1) + '☆' * (4 - data['mastery_level'])}")

        if data['last_reviewed']:
            print(f"Last reviewed: {data['last_reviewed'].strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\nNext review: {data['next_review'].strftime('%Y-%m-%d %H:%M:%S')}")

        # Display Ebbinghaus review schedule
        print("\nEbbinghaus review schedule:")
        for i, interval in enumerate(self.ebbinghaus_intervals):
            review_date = data['added_date'] + timedelta(days=interval)
            status = "✓ Completed" if i < data['review_count'] else "○ Pending"

            if i == 0:
                print(f"  {interval:>2} days ({review_date.strftime('%m-%d %H:%M')}): Initial learning {status}")
            else:
                print(f"  {interval:>2} days ({review_date.strftime('%m-%d %H:%M')}): Review {i} {status}")

    def list_words(self, filter_type: str = "all"):
        """
        List all words
        """
        if not self.words:
            print("No words in memory system.")
            return

        print(f"\n{'Word':<20} {'Definition':<40}")
        print("-" * 70)

        for word, data in self.words.items():
            meanings = data['info']['meanings']
            first_meaning = meanings[0] if meanings else "No definition"
            if len(first_meaning) > 35:
                first_meaning = first_meaning[:35] + "..."

            # Apply filter
            show = True
            if filter_type == "for_review":
                show = data['next_review'] <= datetime.now()
            elif filter_type == "mastered":
                show = data['mastery_level'] >= 3

            if show:
                print(f"{word:<20} {first_meaning:<40}")

        print(f"\nTotal: {len(self.words)} words")

    def export_words(self, filename: str = "words_export.txt"):
        """
        Export all words to text file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Vocabulary Memory List\n")
            f.write(f"Export time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for word, data in self.words.items():
                f.write(f"Word: {data['info']['word']}\n")

                if data['info'].get('phonetic'):
                    f.write(f"Phonetic: /{data['info']['phonetic']}/\n")

                f.write("Definitions:\n")
                for i, meaning in enumerate(data['info']['meanings'], 1):
                    f.write(f"  {i}. {meaning}\n")

                if data['info'].get('examples'):
                    f.write("Examples:\n")
                    for i, example in enumerate(data['info']['examples'], 1):
                        f.write(f"  {i}. {example}\n")

                f.write(f"Added: {data['added_date'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reviews: {data['review_count']}\n")
                f.write(f"Mastery: {'★' * (data['mastery_level'] + 1) + '☆' * (4 - data['mastery_level'])}\n")
                f.write(f"Next review: {data['next_review'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 40 + "\n\n")

        print(f"✓ Words exported to: {filename}")

    def run_interactive(self):
        """
        Run interactive command-line interface
        """
        while True:
            print("\n" + "="*50)
            print("Vocabulary Memory System - Based on Ebbinghaus Forgetting Curve")
            print("="*50)

            # Check for words needing review
            words_to_review = self.get_words_for_review()
            if words_to_review:
                print(f"⚠ {len(words_to_review)} words need review!")

            print("\n1. Add new word")
            print("2. Review words")
            print("3. View review schedule")
            print("4. List all words")
            print("5. Export words")
            print("6. View word details")
            print("7. Exit")

            choice = input("\nSelect option (1-7): ").strip()

            if choice == '1':
                word = input("Enter word to memorize: ").strip()
                if word:
                    self.add_word(word)

            elif choice == '2':
                words_to_review = self.get_words_for_review()
                if not words_to_review:
                    print("No words need review at this time.")
                    continue

                print(f"\n{len(words_to_review)} words need review:")
                for i, word in enumerate(words_to_review, 1):
                    print(f"{i}. {word}")

                selection = input("\nEnter word number (or press Enter to review all): ").strip()

                if selection == '':
                    # Review all
                    for word in words_to_review:
                        self.review_word(word)
                else:
                    try:
                        idx = int(selection) - 1
                        if 0 <= idx < len(words_to_review):
                            self.review_word(words_to_review[idx])
                        else:
                            print("Invalid selection!")
                    except ValueError:
                        print("Please enter a valid number!")

            elif choice == '3':
                word = input("Enter word to view schedule (press Enter for all): ").strip()
                if word:
                    self.show_review_schedule(word)
                else:
                    self.show_review_schedule()

            elif choice == '4':
                print("\n1. All words")
                print("2. Words needing review")
                print("3. Mastered words")
                list_choice = input("Select: ").strip()

                if list_choice == '1':
                    self.list_words("all")
                elif list_choice == '2':
                    self.list_words("for_review")
                elif list_choice == '3':
                    self.list_words("mastered")
                else:
                    print("Invalid selection!")

            elif choice == '5':
                filename = input("Enter export filename (default: words_export.txt): ").strip()
                if not filename:
                    filename = "words_export.txt"
                self.export_words(filename)

            elif choice == '6':
                word = input("Enter word to view details: ").strip()
                if word in self.words:
                    self.display_word_info(self.words[word]['info'])
                else:
                    print(f"Word '{word}' not found!")

            elif choice == '7':
                print("Thank you for using the system. Goodbye!")
                break

            else:
                print("Invalid selection, please try again!")

def main():
    parser = argparse.ArgumentParser(description='Vocabulary memory system based on Ebbinghaus forgetting curve')
    parser.add_argument('--add', '-a', help='Add new word')
    parser.add_argument('--review', '-r', action='store_true', help='Start review')
    parser.add_argument('--list', '-l', action='store_true', help='List all words')
    parser.add_argument('--schedule', '-s', help='View word review schedule')
    parser.add_argument('--export', '-e', help='Export words to file')
    parser.add_argument('--interactive', '-i', action='store_true', help='Enter interactive mode')

    args = parser.parse_args()
    system = WordMemorySystem()

    if args.add:
        system.add_word(args.add)
    elif args.review:
        words_to_review = system.get_words_for_review()
        if words_to_review:
            for word in words_to_review:
                system.review_word(word)
        else:
            print("No words need review.")
    elif args.list:
        system.list_words()
    elif args.schedule:
        system.show_review_schedule(args.schedule)
    elif args.export:
        system.export_words(args.export)
    elif args.interactive:
        system.run_interactive()
    else:
        # Default to interactive mode
        system.run_interactive()

if __name__ == "__main__":
    main()
