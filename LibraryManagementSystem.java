// Save this entire code in a single file named: LibraryManagementSystem.java

import java.util.ArrayList;
import java.util.Scanner;

public class LibraryManagementSystem {
    // Main class with the entry point
    public static void main(String[] args) {
        Library library = new Library();
        library.start();
    }
}

// Library class that contains all the functionality
class Library {
    private ArrayList<Book> books = new ArrayList<>();
    private ArrayList<Member> members = new ArrayList<>();
    private ArrayList<Transaction> transactions = new ArrayList<>();
    private int transactionCount = 1;
    private Scanner scanner = new Scanner(System.in);

    public void start() {
        System.out.println("Welcome to the Library Management System!");

        while (true) {
            System.out.println("\nLibrary Management System Menu:");
            System.out.println("1. Add Book");
            System.out.println("2. Display Books");
            System.out.println("3. Add Member");
            System.out.println("4. Display Members");
            System.out.println("5. Borrow Book");
            System.out.println("6. Display Transactions");
            System.out.println("7. Exit");
            System.out.print("Enter your choice (1-7): ");

            int choice;
            try {
                choice = scanner.nextInt();
                scanner.nextLine(); // Consume the newline
            } catch (Exception e) {
                System.out.println("Please enter a valid number!");
                scanner.nextLine(); // Clear the invalid input
                continue;
            }

            switch (choice) {
                case 1:
                    addBook();
                    break;
                case 2:
                    displayBooks();
                    break;
                case 3:
                    addMember();
                    break;
                case 4:
                    displayMembers();
                    break;
                case 5:
                    borrowBook();
                    break;
                case 6:
                    displayTransactions();
                    break;
                case 7:
                    System.out.println("Thank you for using the Library Management System. Goodbye!");
                    scanner.close();
                    return;
                default:
                    System.out.println("Invalid choice! Please enter a number between 1 and 7.");
            }
        }
    }

    // Method to add a new book
    private void addBook() {
        System.out.print("Enter Book ID: ");
        int bookId = scanner.nextInt();
        scanner.nextLine(); // Consume the newline
        System.out.print("Enter Title: ");
        String title = scanner.nextLine();
        System.out.print("Enter Author: ");
        String author = scanner.nextLine();
        System.out.print("Enter Price: ");
        double price = scanner.nextDouble();

        books.add(new Book(bookId, title, author, price));
        System.out.println("Book added successfully!");
    }

    // Method to display all books
    private void displayBooks() {
        if (books.isEmpty()) {
            System.out.println("No books in the library yet!");
            return;
        }

        for (Book book : books) {
            book.displayBookDetails();
            System.out.println("----------------------");
        }
    }

    // Method to add a new member
    private void addMember() {
        System.out.print("Enter Member ID: ");
        int memberId = scanner.nextInt();
        scanner.nextLine();
        System.out.print("Enter Name: ");
        String name = scanner.nextLine();
        System.out.print("Enter Membership Type (Regular/Premium): ");
        String membershipType = scanner.nextLine();

        if (membershipType.equalsIgnoreCase("Regular")) {
            members.add(new RegularMember(memberId, name));
        } else if (membershipType.equalsIgnoreCase("Premium")) {
            members.add(new PremiumMember(memberId, name));
        } else {
            System.out.println("Invalid membership type. Please enter 'Regular' or 'Premium'.");
            return;
        }
        System.out.println("Member added successfully!");
    }

    // Method to display all members
    private void displayMembers() {
        if (members.isEmpty()) {
            System.out.println("No members registered yet!");
            return;
        }

        for (Member member : members) {
            member.displayMemberDetails();
            System.out.println("----------------------");
        }
    }

    // Method to borrow a book
    private void borrowBook() {
        if (books.isEmpty() || members.isEmpty()) {
            System.out.println("Please add books and members first!");
            return;
        }

        System.out.print("Enter Book ID to Borrow: ");
        int bookId = scanner.nextInt();
        System.out.print("Enter Member ID: ");
        int memberId = scanner.nextInt();
        scanner.nextLine();
        System.out.print("Enter Borrow Date (YYYY-MM-DD): ");
        String borrowDate = scanner.nextLine();

        // Check if member exists
        boolean memberExists = false;
        for (Member member : members) {
            if (member.getMemberId() == memberId) {
                memberExists = true;
                break;
            }
        }

        if (!memberExists) {
            System.out.println("Member not found!");
            return;
        }

        // Check if book exists and is available
        for (Book book : books) {
            if (book.getBookId() == bookId) {
                if (book.isAvailable()) {
                    book.updateAvailability(false);
                    transactions.add(new Transaction(transactionCount++, bookId, memberId, borrowDate));
                    System.out.println("Book borrowed successfully!");
                    return;
                } else {
                    System.out.println("Book is already borrowed!");
                    return;
                }
            }
        }
        System.out.println("Book not found!");
    }

    // Method to display all transactions
    private void displayTransactions() {
        if (transactions.isEmpty()) {
            System.out.println("No transactions yet!");
            return;
        }

        for (Transaction transaction : transactions) {
            transaction.displayTransactionDetails();
            System.out.println("----------------------");
        }
    }
}

// Book class
class Book {
    private int bookId;
    private String title;
    private String author;
    private double price;
    private boolean availabilityStatus;

    public Book(int bookId, String title, String author, double price) {
        this.bookId = bookId;
        this.title = title;
        this.author = author;
        this.price = price;
        this.availabilityStatus = true;
    }

    public int getBookId() {
        return bookId;
    }

    public boolean isAvailable() {
        return availabilityStatus;
    }

    public void displayBookDetails() {
        System.out.println("Book ID: " + bookId);
        System.out.println("Title: " + title);
        System.out.println("Author: " + author);
        System.out.println("Price: $" + price);
        System.out.println("Available: " + (availabilityStatus ? "Yes" : "No"));
    }

    public void updateAvailability(boolean status) {
        this.availabilityStatus = status;
    }
}

// Member class
class Member {
    private int memberId;
    private String name;
    private String membershipType;

    public Member(int memberId, String name, String membershipType) {
        this.memberId = memberId;
        this.name = name;
        this.membershipType = membershipType;
    }

    public int getMemberId() {
        return memberId;
    }

    public void displayMemberDetails() {
        System.out.println("Member ID: " + memberId);
        System.out.println("Name: " + name);
        System.out.println("Membership Type: " + membershipType);
    }
}

// Regular Member (Subclass of Member)
class RegularMember extends Member {
    public RegularMember(int memberId, String name) {
        super(memberId, name, "Regular");
    }
}

// Premium Member (Subclass of Member)
class PremiumMember extends Member {
    public PremiumMember(int memberId, String name) {
        super(memberId, name, "Premium");
    }
}

// Transaction class
class Transaction {
    private int transactionId;
    private int bookId;
    private int memberId;
    private String borrowDate;

    public Transaction(int transactionId, int bookId, int memberId, String borrowDate) {
        this.transactionId = transactionId;
        this.bookId = bookId;
        this.memberId = memberId;
        this.borrowDate = borrowDate;
    }

    public void displayTransactionDetails() {
        System.out.println("Transaction ID: " + transactionId);
        System.out.println("Book ID: " + bookId);
        System.out.println("Member ID: " + memberId);
        System.out.println("Borrow Date: " + borrowDate);
    }
}