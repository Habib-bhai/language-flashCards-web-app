import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import json
import numpy as np
import plotly.express as px

# Initialize session state
if 'current_card' not in st.session_state:
    st.session_state.current_card = None
if 'cards_due' not in st.session_state:
    st.session_state.cards_due = []
if 'progress' not in st.session_state:
    st.session_state.progress = {}
if 'quiz_score' not in st.session_state:
    st.session_state.quiz_score = 0
if 'total_reviews' not in st.session_state:
    st.session_state.total_reviews = 0
if 'view_index' not in st.session_state:
    st.session_state.view_index = 0  # Index for viewing flashcards

# Spaced repetition intervals (in days)
INTERVALS = [1, 3, 7, 14, 30, 90]

class Flashcard:
    def __init__(self, word, translation, level=0, next_review=None):
        self.word = word
        self.translation = translation
        self.level = level
        self.next_review = next_review or datetime.now()
        self.reviews = 0
        self.correct = 0

    def to_dict(self):
        return {
            'word': self.word,
            'translation': self.translation,
            'level': self.level,
            'next_review': self.next_review.isoformat(),
            'reviews': self.reviews,
            'correct': self.correct
        }

    @classmethod
    def from_dict(cls, data):
        card = cls(data['word'], data['translation'], data['level'])
        card.next_review = datetime.fromisoformat(data['next_review'])
        card.reviews = data.get('reviews', 0)
        card.correct = data.get('correct', 0)
        return card

def save_cards(cards):
    with open('flashcards.json', 'w') as f:
        json.dump([card.to_dict() for card in cards], f)

def load_cards():
    try:
        with open('flashcards.json', 'r') as f:
            return [Flashcard.from_dict(card_data) for card_data in json.load(f)]
    except FileNotFoundError:
        return []

def update_card_status(card, correct):
    card.reviews += 1
    if correct:
        card.correct += 1
        card.level = min(len(INTERVALS) - 1, card.level + 1)
    else:
        card.level = max(0, card.level - 1)
    card.next_review = datetime.now() + timedelta(days=INTERVALS[card.level])

def create_quiz(cards, current_word):
    correct_card = next(card for card in cards if card.word == current_word)
    options = [correct_card.translation]
    available_cards = [card for card in cards if card.word != current_word]
    options.extend(random.sample([card.translation for card in available_cards], 
                               min(3, len(available_cards))))
    random.shuffle(options)
    return options, correct_card.translation

def main():
    st.title("Language Learning Flashcard App 🗣️")
    
    # Load existing cards
    cards = load_cards()
    
    # Sidebar for adding new cards
    with st.sidebar:
        st.header("Add New Flashcard")
        word = st.text_input("Word")
        translation = st.text_input("Translation")
        if st.button("Add Card"):
            if word and translation:
                cards.append(Flashcard(word, translation))
                save_cards(cards)
                st.success("Card added successfully!")
        
        st.divider()
        st.header("Study Statistics")
        if cards:
            total_cards = len(cards)
            total_reviews = sum(card.reviews for card in cards)
            avg_accuracy = np.mean([card.correct/card.reviews if card.reviews > 0 else 0 
                                  for card in cards]) * 100
            
            st.metric("Total Cards", total_cards)
            st.metric("Total Reviews", total_reviews)
            st.metric("Average Accuracy", f"{avg_accuracy:.1f}%")
            
            # Performance chart
            if total_reviews > 0:
                review_data = pd.DataFrame([
                    {'word': card.word, 
                     'accuracy': (card.correct/card.reviews)*100 if card.reviews > 0 else 0}
                    for card in cards
                ])
                fig = px.bar(review_data, x='word', y='accuracy',
                            title="Word-wise Performance",
                            labels={'accuracy': 'Accuracy (%)', 'word': 'Word'})
                st.plotly_chart(fig)

    # Main app interface
    tab1, tab2, tab3 = st.tabs(["Review Cards", "Quiz Mode", "View Flashcards"])
    
    with tab1:
        # Get due cards
        due_cards = [card for card in cards if card.next_review <= datetime.now()]
        
        if due_cards:
            if st.session_state.current_card is None:
                st.session_state.current_card = random.choice(due_cards)
            
            card = st.session_state.current_card
            
            st.header(card.word)
            show_translation = st.button("Show Translation")
            
            if show_translation:
                st.header(card.translation)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("I remembered it ✅"):
                        update_card_status(card, True)
                        save_cards(cards)
                        st.session_state.current_card = None
                        st.rerun()
                
                with col2:
                    if st.button("I forgot it ❌"):
                        update_card_status(card, False)
                        save_cards(cards)
                        st.session_state.current_card = None
                        st.rerun()
        else:
            st.success("No cards due for review! 🎉")
    
    with tab2:
        if cards:
            if st.session_state.current_card is None:
                st.session_state.current_card = random.choice(cards)
            
            card = st.session_state.current_card
            st.header(f"What is the translation of: {card.word}?")
            
            options, correct_answer = create_quiz(cards, card.word)
            user_answer = st.radio("Choose the correct translation:", options)
            
            if st.button("Submit Answer"):
                if user_answer == correct_answer:
                    st.success("Correct! 🎉")
                    st.session_state.quiz_score += 1
                else:
                    st.error(f"Wrong! The correct answer was: {correct_answer}")
                
                st.session_state.total_reviews += 1
                st.session_state.current_card = None
                
                progress_col1, progress_col2 = st.columns(2)
                with progress_col1:
                    st.metric("Score", f"{st.session_state.quiz_score}/{st.session_state.total_reviews}")
                with progress_col2:
                    accuracy = (st.session_state.quiz_score/st.session_state.total_reviews)*100
                    st.metric("Accuracy", f"{accuracy:.1f}%")
                
                if st.button("Next Question"):
                    st.rerun()
        else:
            st.warning("Add some flashcards to start the quiz!")
    
    with tab3:
        if cards:
            st.header("View Flashcards")
            
            # Display current flashcard
            card = cards[st.session_state.view_index]
            st.subheader(f"Card {st.session_state.view_index + 1} of {len(cards)}")
            st.write(f"**Word:** {card.word}")
            st.write(f"**Translation:** {card.translation}")
            st.write(f"**Level:** {card.level}")
            st.write(f"**Next Review:** {card.next_review.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Reviews:** {card.reviews}")
            st.write(f"**Correct Answers:** {card.correct}")
            
            # Navigation buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Previous"):
                    st.session_state.view_index = max(0, st.session_state.view_index - 1)
                    st.rerun()
            with col2:
                if st.button("Next"):
                    st.session_state.view_index = min(len(cards) - 1, st.session_state.view_index + 1)
                    st.rerun()
        else:
            st.warning("No flashcards available. Add some flashcards to view them.")

if __name__ == "__main__":
    main()