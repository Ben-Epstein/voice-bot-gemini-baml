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

client<llm> ModalGemma3_4B {
  provider openai
  options {
    http {
      // Max time to establish connection to provider
      connect_timeout_ms 500  // 0.5 seconds
      time_to_first_token_timeout_ms 500 // 0.5 seconds
      // Maximum time between consecutive tokens
      idle_timeout_ms 500  // 0.5 seconds
      // Total time
      request_timeout_ms 5000 // 5 seconds. To prevent bug-cases where the model generates continuously in a loop
    }
    model "google/gemma-3-4b-it"
    api_key env.VLLM_API_KEY
    base_url env.MODAL_VLLM_URL
    temperature 0.0
    seed 42
  }
}

client<llm> AppModel {
  provider fallback
  retry_policy Constant
  options {
   strategy [ModalGemma3_4B, Gemini]
  }
}

retry_policy Constant {
  max_retries 3
  strategy {
    type constant_delay
    delay_ms 50
  }
}

function GenerateQuestion(conversation: string) -> string {
  client ModalGemma3_4B
  prompt #"
    Given the following conversation from a car rental inquiry call,
    generate one relevant question that the caller might ask next.
    
    Conversation: {{ conversation }}
    
    Next Question:
  "#
}

// Extract questions from the caller
function ExtractQuestions(conversation: string) -> string[] {
  client AppModel
  prompt #"
    {{ _.role("user" )}}

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
  client AppModel
  prompt #"
    {{ _.role("user" )}}
    Extract renter profile information from this car rental inquiry conversation.
    Only include information that was explicitly mentioned. Use null for missing fields.
    
    Conversation: {{ conversation }}
    
    {{ ctx.output_format }}
  "#
}
