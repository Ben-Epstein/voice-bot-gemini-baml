// BAML configuration for intent and question extraction

client<llm> Gemini {
  provider baml-gemini-chat
  options {
    model "gemini-1.5-flash"
    api_key env.GEMINI_API_KEY
  }
}

// Extract caller intent from conversation
function ExtractIntent(conversation: string) -> string {
  client Gemini
  prompt #"
    Given the following conversation from a car rental inquiry call, 
    extract the primary intent of the caller in one short sentence.
    
    Conversation: {{ conversation }}
    
    Intent:
  "#
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
class RenterProfile {
  name string? @description("Name of the caller if mentioned")
  phone string? @description("Phone number if mentioned")
  email string? @description("Email address if mentioned")
  rental_dates string? @description("Desired rental dates if mentioned")
  car_preferences string[] @description("Car type or feature preferences mentioned")
  budget_range string? @description("Budget range if mentioned")
  location string? @description("Pickup/dropoff location if mentioned")
  additional_notes string? @description("Any other relevant information")
}

function ExtractRenterProfile(conversation: string) -> RenterProfile {
  client Gemini
  prompt #"
    Extract renter profile information from this car rental inquiry conversation.
    Only include information that was explicitly mentioned. Use null for missing fields.
    
    Conversation: {{ conversation }}
    
    {{ ctx.output_format }}
  "#
}
