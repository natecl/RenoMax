import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

const mockHomes = [
  {
    externalId: "1",
    address: "123 Main St",
    city: "Springfield",
    state: "IL",
    price: 300000,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1800,
  },
  {
    externalId: "2",
    address: "456 Oak Ave",
    city: "Springfield",
    state: "IL",
    price: 550000,
    bedrooms: 4,
    bathrooms: 3,
    sqft: 2600,
  },
];

describe("App flow", () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHomes,
    });
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test("searches by zip and filters results", async () => {
    render(<App />);

    fireEvent.change(screen.getByPlaceholderText(/enter zip code/i), {
      target: { value: "12345" },
    });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));

    expect(await screen.findByText(/123 Main St/i)).toBeInTheDocument();
    expect(screen.getByText(/456 Oak Ave/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/minimum beds/i), {
      target: { value: "4" },
    });
    fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

    await waitFor(() => {
      expect(screen.queryByText(/123 Main St/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/456 Oak Ave/i)).toBeInTheDocument();
  });
});
