type CarType = ("sedan" | "suv" | "truck" | "van" | "coupe" | "convertible" | "hatchback" | "wagon" | "sports"| "electric" | "luxury" | "other")
type SaleType = ("rental" | "sale" | "both")
type PriceUnit = ("usd_per_day" | "usd")

class CarInfo {
  make string
  model string
  year int
  type CarType
  sale_type SaleType
  price int          @description("For sale price OR rental price per day")
  price_unit PriceUnit
  fuel_efficiency int
  features string[]
  horsepower int
  seats int
}