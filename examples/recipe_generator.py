from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import ai_model
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Ingredient(BaseModel):
    name: str
    amount: str
    unit: str = Field(..., description="Unit of measurement (e.g., cups, grams, pieces)")

class Recipe(BaseModel):
    title: str = Field(..., description="A catchy and descriptive title for the recipe")
    description: str = Field(..., description="Brief description of the dish and its flavors")
    ingredients: List[Ingredient]
    instructions: List[str] = Field(..., description="Step by step cooking instructions")
    prep_time: str = Field(..., description="Preparation time (e.g., '15 minutes')")
    cook_time: str = Field(..., description="Cooking time (e.g., '30 minutes')")
    servings: int = Field(..., description="Number of servings this recipe yields")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")

@ai_model
def generate_recipe(
    cuisine: str,
    dietary_restrictions: List[str] = None,
    max_prep_time: str = None,
) -> Recipe:
    """Generate a recipe based on cuisine type and dietary restrictions.
    
    Args:
        cuisine: Type of cuisine (e.g., Italian, Japanese, Mexican)
        dietary_restrictions: List of dietary restrictions (e.g., vegetarian, gluten-free)
        max_prep_time: Maximum preparation time (e.g., '30 minutes')
    
    Returns:
        A complete recipe with ingredients and instructions
    """
    pass

def display_recipe(recipe: Recipe):
    """Helper function to display the recipe nicely"""
    print(f"\n{'='*50}")
    print(f"📖 {recipe.title.upper()}")
    print(f"{'='*50}\n")
    
    print(f"Description: {recipe.description}\n")
    print(f"Difficulty: {recipe.difficulty}")
    print(f"Prep Time: {recipe.prep_time}")
    print(f"Cook Time: {recipe.cook_time}")
    print(f"Servings: {recipe.servings}\n")
    
    print("Ingredients:")
    print("-"*20)
    for ingredient in recipe.ingredients:
        print(f"• {ingredient.amount} {ingredient.unit} {ingredient.name}")
    
    print("\nInstructions:")
    print("-"*20)
    for i, step in enumerate(recipe.instructions, 1):
        print(f"{i}. {step}")
    print("\n")

def main():
    # Example usage
    try:
        recipe = generate_recipe(
            cuisine="Japanese",
            dietary_restrictions=["vegetarian"],
            max_prep_time="30 minutes"
        )
        display_recipe(recipe)
        
    except Exception as e:
        print(f"Error generating recipe: {str(e)}")

if __name__ == "__main__":
    main()