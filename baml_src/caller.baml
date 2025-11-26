// BAML configuration for intent and question extraction

client<llm> Gemini {
  provider vertex-ai
    options {
    model gemini-2.5-flash
    project_id env.PROJECT_ID
    location env.GEMINI_REGION
    // base_url "https://aiplatform.googleapis.com/v1/projects/grotto-prod/locations/global/publishers/google/models"
    generation_config {
      temperature 0.0
      seed 42
      top_p 0.95
      thinkingConfig {
          thinkingBudget 0
    }
    }
  }
}


// Extract questions from the caller
function ExtractQuestions(conversation: string) -> string[] {
  client Gemini
  prompt #"
    Given the following conversation from a car rental inquiry call,
    extract all the distinct questions the caller has asked.
    Return only the questions, one per line.
    
    Conversation: {{ conversation }}
    
    Questions:
  "#
}

// Extract renter profile information
class CallerProfile {
  name string? @description("Name of the caller if mentioned")
  phone string? @description("Phone number if mentioned")
  email string? @description("Email address if mentioned")
  rental_dates string? @description("Desired rental dates if mentioned")
  car_preferences string[] @description("Car type or feature preferences mentioned")
  budget_low float?
  budget_high float?
  location string? @description("Pickup/dropoff location if mentioned")
  additional_notes string[] @description("Any other relevant information")
  intent ("buying" | "renting" | "inquiry" | "other")? @description("Primary intent of the caller")
}

class CallerData {
  profile CallerProfile
  questions string[]
}

function ExtractRenterProfile(conversation: string) -> CallerProfile {
  client Gemini
  prompt #"
    Extract renter profile information from this car rental inquiry conversation.
    Only include information that was explicitly mentioned. Use null for missing fields.
    
    Conversation: {{ conversation }}
    
    {{ ctx.output_format }}
  "#
}
