"""
Demo data generator — 40 synthetic students, 4 DSA questions.
Pre-clustered data for instant hackathon demo (no ML model needed).
"""
import random
from uuid import uuid4

EXAM_CODE = "DSA-2024-MID"
EXAM_TITLE = "Data Structures & Algorithms — Mid Term"

RUBRIC = {
    "Q1": {
        "q_text": "What is a Binary Search Tree (BST)? Explain its key properties.",
        "max_marks": 5,
        "keywords": ["binary search tree", "BST", "left subtree", "right subtree",
                     "less than", "greater than", "O(log n)", "sorted", "in-order"],
    },
    "Q2": {
        "q_text": "Differentiate Stack and Queue. Give one real-world example each.",
        "max_marks": 5,
        "keywords": ["LIFO", "FIFO", "push", "pop", "enqueue", "dequeue",
                     "browser history", "printer", "call stack", "task queue"],
    },
    "Q3": {
        "q_text": "Explain Merge Sort. What is its time complexity?",
        "max_marks": 5,
        "keywords": ["merge sort", "divide and conquer", "O(n log n)", "recursive",
                     "merge", "sorted subarrays", "stable"],
    },
    "Q4": {
        "q_text": "What is a Hash Table? What is collision and how is it handled?",
        "max_marks": 5,
        "keywords": ["hash table", "hash function", "key-value", "collision",
                     "chaining", "open addressing", "linear probing"],
    },
}

# --- Answer templates per question per cluster type ---

Q1 = {
    "correct": [
        "A Binary Search Tree (BST) is a tree data structure where each node has at most two children. The key property: for any node, all values in its left subtree are less than the node's value and all values in its right subtree are greater. This enforces O(log n) average-case search time. In-order traversal yields elements in sorted order. No duplicate keys are allowed.",
        "BST is a hierarchical data structure. Properties: 1) Each node has at most 2 children (left, right). 2) Left child < Parent < Right child. 3) Both subtrees are themselves BSTs. 4) No duplicates. This structure allows binary search — eliminate half the tree at each step, giving O(log n) average time for search, insert, delete.",
        "A BST is a binary tree with the ordering property: left subtree contains only nodes with keys smaller than the root, right subtree contains only nodes with keys greater than the root, and this property holds recursively for every subtree. The sorted structure enables O(log n) search in the average case and O(n) in the worst case when the tree is unbalanced.",
        "Binary Search Tree is a data structure where for every node N: all keys in left subtree < N.key and all keys in right subtree > N.key. Key properties: (1) Maintains BST property at every node (2) In-order traversal gives sorted output (3) O(log n) average search time (4) No duplicate values. Used for: searching, sorting, and range queries.",
        "A BST is a binary tree where the left child is always less than the parent and the right child is always greater. Properties: ordered structure, O(log n) avg search/insert/delete, in-order traversal = sorted sequence. Disadvantage: can degenerate to O(n) if not balanced (e.g., inserting sorted data). Self-balancing BSTs like AVL trees fix this.",
        "BST is a form of binary tree adhering to the BST invariant: leftChild.key < node.key < rightChild.key for every node. This property means we can perform binary search on the tree. Operations: search O(log n) avg, O(n) worst. Insert and delete also O(log n) avg. In-order traversal prints all keys in ascending sorted order.",
    ],
    "partial": [
        "A Binary Search Tree is a tree where each node can have at most two children called left and right. It is used for fast searching and retrieval of data. Insert and delete operations can also be performed efficiently.",
        "BST is a tree structure used in computer science for searching. Each node has a left child and right child. The tree can be traversed using in-order, pre-order or post-order traversal methods.",
        "A BST is a binary tree used for efficient data storage and retrieval. It supports operations like insert, delete and search. The time complexity of these operations is generally good, making BST suitable for many applications.",
        "Binary Search Tree is a data structure where each node has two children. It is commonly used for implementing dynamic sets and lookup tables. BST operations include search, insert, delete and traversal.",
        "A BST is a special type of binary tree that allows fast searching. Each node contains a value and pointers to two children. The structure allows for efficient data management in computer programs.",
    ],
    "incorrect": [
        "A Binary Search Tree is a tree where each node has two children and the parent is always greater than both its children. It is similar to a max-heap where the root has the largest value. This makes finding the maximum element very fast.",
        "BST is a complete binary tree where all levels are completely filled except possibly the last level. Every parent node has exactly two children and is larger than or equal to its children. This property allows the minimum element to always be at the root.",
        "A Binary Search Tree is a tree where nodes are arranged level by level from top to bottom and left to right. The root is at level 0, its children at level 1, and so on. This arrangement makes it a complete binary tree useful for heap operations.",
        "BST is a data structure where all elements in the odd levels are less than elements in even levels. The tree is balanced and used mainly for priority queue implementations. Each insertion maintains the heap property.",
        "A Binary Search Tree is a balanced binary tree where the left and right subtrees of any node differ in height by at most one. This balancing property ensures O(log n) operations for all standard operations.",
    ],
    "vague": [
        "BST is a tree data structure used in programming. It is efficient for searching.",
        "A Binary Search Tree stores data in a tree format and allows binary search.",
        "BST is used for searching and sorting. It has nodes connected by edges.",
    ],
}

Q2 = {
    "correct": [
        "Stack is a LIFO (Last In First Out) data structure. Operations: push (add to top), pop (remove from top). Real-world example: browser back button — the last page visited is the first to go back to. Queue is FIFO (First In First Out). Operations: enqueue (add to rear), dequeue (remove from front). Real-world example: printer queue — documents print in the order they were submitted.",
        "Stack uses LIFO — the last element inserted is the first to be removed. Think of a stack of plates: you add and remove from the top. Used in: function call stack, undo operations, expression evaluation. Queue uses FIFO — first element in is first out. Like a ticket counter: first person in line is served first. Used in: CPU scheduling, BFS, message queues.",
        "Difference: Stack is LIFO (push/pop at same end) while Queue is FIFO (enqueue at rear, dequeue at front). Stack example: browser history — pressing back pops the most recent URL. Queue example: task scheduler — processes run in the order they arrive, preventing starvation.",
        "Stack (LIFO): elements are added and removed from the same end (top). Supports push() and pop(). Real-world use: undo/redo in text editors — most recent action is undone first. Queue (FIFO): elements added at rear, removed from front. Supports enqueue() and dequeue(). Real-world use: print spooler — jobs printed in order received.",
        "A Stack is LIFO (Last In First Out) — latest item added is first removed. Used for: call stack in programming, bracket matching, DFS. A Queue is FIFO (First In First Out) — oldest item is processed first. Used for: BFS traversal, printer job queuing, OS process scheduling. Key ops — Stack: push/pop. Queue: enqueue/dequeue.",
    ],
    "partial": [
        "Stack is a data structure where elements are added and removed from the top. It follows LIFO order. Queue is different — elements are added at the back and removed from the front. Stack is used in recursion and Queue is used in breadth-first search.",
        "Stack follows LIFO principle while Queue follows FIFO principle. In stack, the last inserted element comes out first. In queue, the first inserted element comes out first. Both are linear data structures used in different algorithms.",
        "Stack is LIFO and Queue is FIFO. Stack has push and pop operations. Queue has enqueue and dequeue operations. Stack is used for implementing recursion while Queue is used for implementing BFS algorithm.",
        "The main difference between Stack and Queue is the order of removal. Stack removes the most recently added element (LIFO) while Queue removes the oldest element (FIFO). Both are fundamental data structures in computer science.",
    ],
    "confused": [
        "Stack is a FIFO data structure where elements are added at the front and removed from the rear. Queue is LIFO where elements are added and removed from both ends. Stack is used in graph traversal and Queue in recursion.",
        "Stack and Queue are both linear data structures. Stack uses FIFO (first element is the last to be removed) while Queue uses LIFO. Both can be implemented using arrays or linked lists.",
        "Stack uses FIFO method: first added element is first removed, like a queue at a shop. Queue uses LIFO method: last added is first removed. The main application of stack is OS scheduling and queue is for expression evaluation.",
    ],
}

Q3 = {
    "correct": [
        "Merge Sort is a divide-and-conquer algorithm. Steps: (1) Divide the array into two equal halves. (2) Recursively sort each half. (3) Merge the two sorted halves into one sorted array. Time complexity: O(n log n) for all cases (best, average, worst). Space complexity: O(n) auxiliary space needed for merging. It is a stable sorting algorithm.",
        "Merge Sort works by recursively splitting the array into halves until each subarray has one element, then merging the sorted subarrays back together. T(n) = 2T(n/2) + O(n). Solving this recurrence gives O(n log n). Advantages over QuickSort: stable sort, guaranteed O(n log n) worst case. Disadvantage: needs O(n) extra memory.",
        "Merge Sort uses divide and conquer. Divide: split array of n elements into two halves of n/2 each. Conquer: recursively sort both halves. Combine: merge two sorted arrays into one sorted array in O(n) time. Recurrence: T(n) = 2T(n/2) + cn → O(n log n). Best/average/worst all O(n log n). Stable, not in-place.",
        "Time complexity of Merge Sort: O(n log n) in all cases. The algorithm divides the array log n times and each level of merging takes O(n) work total, giving n × log n = O(n log n). The merge step combines two sorted arrays by comparing elements one by one. It is a stable sort meaning equal elements maintain their relative order.",
        "Merge Sort: divide the array into 2 halves, recursively sort each, then merge. The key insight is that merging two sorted arrays takes O(n). Since we divide log n times, total complexity = O(n log n). This holds for best, average and worst cases — unlike QuickSort which can degrade to O(n²). Space: O(n).",
    ],
    "partial": [
        "Merge Sort is a sorting algorithm that uses the divide and conquer technique. It divides the list into smaller sub-lists, sorts them, and then merges them back. The time complexity is O(n log n) which is better than bubble sort O(n²).",
        "Merge Sort divides the array into two halves and sorts each half recursively, then merges them. It has O(n log n) time complexity and is more efficient than selection sort or insertion sort for large datasets.",
        "The time complexity of Merge Sort is O(n log n). It works by dividing the array and merging sorted portions. It requires extra space for the merging process.",
        "Merge Sort is a recursive sorting algorithm with O(n log n) complexity. It merges sorted subarrays to produce the final sorted output.",
    ],
    "incorrect": [
        "Merge Sort has time complexity O(n²) in the worst case because it compares each element with every other element while merging. In the best case, when the array is already sorted, it runs in O(n) time.",
        "Merge Sort works by selecting a pivot element, partitioning the array around the pivot, and recursively sorting the partitions. Its average time complexity is O(n log n) and worst case is O(n²) when the pivot is always the smallest or largest element.",
        "Merge Sort is an in-place sorting algorithm with O(n log n) time complexity. It sorts elements by dividing and merging without requiring extra memory. Its space complexity is O(1).",
        "Merge Sort time complexity: O(log n) because it keeps dividing the array in half each time. This logarithmic behavior makes it faster than most sorting algorithms.",
    ],
}

Q4 = {
    "correct": [
        "A Hash Table is a data structure that maps keys to values using a hash function. The hash function converts a key into an index in an underlying array. Collision: when two different keys hash to the same index. Handling: (1) Chaining — each slot holds a linked list of entries, (2) Open Addressing — find another slot using linear probing, quadratic probing, or double hashing.",
        "Hash Table stores key-value pairs. Hash function: h(key) → index in array. Collision occurs when h(k1) = h(k2) for k1 ≠ k2. Collision resolution: (a) Separate Chaining — slot contains a linked list, multiple entries stored at same index, (b) Open Addressing (Linear Probing) — if slot occupied, check next slot: h(k, i) = (h(k) + i) mod m. Load factor determines performance.",
        "Hash Table is a key-value store with O(1) average lookup. A hash function maps keys to array indices. Collision: two keys map to same index. Methods to resolve: 1) Chaining — use a linked list at each bucket (simple but extra memory). 2) Open addressing — probe for next empty slot. Linear probing: index+1, index+2... Quadratic probing: index+1², index+2²...",
        "A Hash Table uses a hash function to compute array index from a key, enabling O(1) average case insert/search/delete. Collision: when two keys produce the same hash. Resolution strategies: (i) Separate Chaining — each index points to a list, handles high load factors well. (ii) Linear Probing — scan ahead for empty slot, simpler but causes clustering.",
        "Hash Table: data structure providing O(1) avg time for get/set/delete. Works by applying hash function to key to get index. Collision occurs when two keys get the same index. Solutions: Chaining (each bucket is a linked list — can store multiple entries) and Open Addressing (find alternate slot via probing — linear, quadratic, or double hashing).",
    ],
    "partial": [
        "A hash table stores data using a hash function to determine where each item goes in an array. A collision happens when two items are placed in the same location. This can be handled using chaining where a linked list is used at each index.",
        "Hash table is a data structure that provides constant time O(1) access to elements using a key. When two keys produce the same hash value, a collision occurs. Collision can be resolved using linear probing where we look at the next available slot.",
        "Hash tables use key-value pairs and a hash function for fast data access. Collisions happen when the hash function produces the same index for different keys. This is resolved using techniques like chaining or probing.",
        "A hash table is an efficient data structure that uses a hash function to index data. Collisions occur and can be resolved using various techniques like open addressing or chaining.",
    ],
    "incorrect": [
        "A hash table is a sorted array of key-value pairs where binary search is used for fast retrieval. Collision occurs when two elements have the same value. This is handled by sorting the array again after each insertion.",
        "Hash table is a tree-based data structure where each key maps to a leaf node. Collision is when two different keys have the same depth in the tree. This is handled by increasing the depth of the tree.",
        "A hash table stores elements in random order using random indices. A collision happens when two elements are stored at adjacent indices. Linear search is used to find elements when they collide.",
    ],
}


def _make_students():
    names = [
        "Aarav Sharma", "Priya Singh", "Rohit Kumar", "Sneha Patel", "Arjun Gupta",
        "Kavya Nair", "Vikram Rao", "Anjali Verma", "Siddharth Joshi", "Meera Iyer",
        "Aditya Mehta", "Pooja Reddy", "Rahul Bose", "Divya Nair", "Amit Tiwari",
        "Neha Kapoor", "Suresh Menon", "Riya Desai", "Karan Malhotra", "Preethi Iyengar",
        "Harish Pillai", "Lakshmi Sundaram", "Dev Patel", "Nisha Bhatt", "Ashok Sinha",
        "Swati Kulkarni", "Nikhil Agarwal", "Pallavi Nair", "Suraj Yadav", "Ananya Das",
        "Vijay Krishnamurthy", "Shreya Ghosh", "Manish Dubey", "Tanisha Saxena", "Rakesh Pandey",
        "Deepa Subramaniam", "Gaurav Chandra", "Ayesha Khan", "Abhishek Mishra", "Ritika Jain",
    ]
    students = []
    for i, name in enumerate(names[:40]):
        students.append({
            "roll_number": f"CS{2024000 + i + 1}",
            "name": name,
            "exam_code": EXAM_CODE,
        })
    return students


def generate_demo_exam() -> dict:
    """
    Returns a fully pre-clustered exam object ready for the grading dashboard.
    No ML models required — instant load for hackathon demo.
    """
    students = _make_students()
    random.seed(42)

    def assign(pool_dict, counts: dict) -> list:
        """Draw answers from pool in specified counts."""
        result = []
        for pool_key, n in counts.items():
            pool = pool_dict[pool_key]
            for j in range(n):
                result.append(pool[j % len(pool)])
        return result

    # Per-question cluster definitions
    q_cluster_defs = {
        "Q1": [
            {"pool_key": "correct",   "count": 14, "label": "Correct – Full BST explanation with ordering property", "type": "correct"},
            {"pool_key": "partial",   "count": 10, "label": "Partial – Mentions binary tree but misses ordering property", "type": "partial"},
            {"pool_key": "incorrect", "count": 8,  "label": "Incorrect – Confused BST with Max-Heap", "type": "incorrect"},
            {"pool_key": "vague",     "count": 5,  "label": "Partial – Very brief, lacks detail", "type": "partial"},
        ],
        "Q2": [
            {"pool_key": "correct",   "count": 15, "label": "Correct – LIFO/FIFO with accurate real-world examples", "type": "correct"},
            {"pool_key": "partial",   "count": 12, "label": "Partial – Correct concepts, no real-world examples", "type": "partial"},
            {"pool_key": "confused",  "count": 8,  "label": "Incorrect – LIFO and FIFO swapped", "type": "incorrect"},
        ],
        "Q3": [
            {"pool_key": "correct",   "count": 13, "label": "Correct – O(n log n), divide & conquer explained", "type": "correct"},
            {"pool_key": "partial",   "count": 11, "label": "Partial – Correct complexity, weak algorithm explanation", "type": "partial"},
            {"pool_key": "incorrect", "count": 10, "label": "Incorrect – Wrong complexity or confused with QuickSort", "type": "incorrect"},
        ],
        "Q4": [
            {"pool_key": "correct",   "count": 14, "label": "Correct – Hash function, collision + resolution methods", "type": "correct"},
            {"pool_key": "partial",   "count": 12, "label": "Partial – Knows collision but vague on resolution", "type": "partial"},
            {"pool_key": "incorrect", "count": 9,  "label": "Incorrect – Fundamentally misunderstood hash table", "type": "incorrect"},
        ],
    }

    pools = {"Q1": Q1, "Q2": Q2, "Q3": Q3, "Q4": Q4}

    exam_clusters: dict = {}
    student_q_map: dict = {s["roll_number"]: {} for s in students}

    for q_num, defs in q_cluster_defs.items():
        pool = pools[q_num]
        rubric = RUBRIC[q_num]
        keywords = rubric["keywords"]
        max_marks = rubric["max_marks"]

        clusters = []
        edge_cases = []
        student_idx = 0

        for ci, cdef in enumerate(defs):
            pk = cdef["pool_key"]
            count = cdef["count"]
            answers_pool = pool[pk]
            members = []

            for j in range(count):
                if student_idx >= len(students):
                    break
                stu = students[student_idx]
                ans_text = answers_pool[j % len(answers_pool)]
                answer = {
                    "q_number": q_num,
                    "text": ans_text,
                    "diagram_present": False,
                    "diagram_description": None,
                    "attempted": True,
                }
                member = {
                    "roll_number": stu["roll_number"],
                    "name": stu["name"],
                    "answer": answer,
                    "combined_text": f"[Text]: {ans_text}",
                }
                members.append(member)
                student_q_map[stu["roll_number"]][q_num] = ans_text
                student_idx += 1

            if not members:
                continue

            matched_kw = [k for k in keywords if any(k.lower() in m["combined_text"].lower() for m in members)]
            kw_pct = len(matched_kw) / len(keywords) if keywords else 0.0
            suggested = round(kw_pct * max_marks, 1)

            cluster_obj = {
                "cluster_id": f"{q_num}_cluster_{ci}",
                "label": cdef["label"],
                "type": cdef["type"],
                "student_count": len(members),
                "students": members,
                "representative": members[0],
                "matched_keywords": matched_kw,
                "keyword_match_pct": round(kw_pct, 2),
                "suggested_score": suggested,
                "graded": False,
                "score": None,
                "feedback": "",
            }
            clusters.append(cluster_obj)

        # 3 edge case students per question (last 3 students of the exam participate)
        edge_student_pool = students[-3:] if len(students) >= 3 else students
        for ei, stu in enumerate(edge_student_pool):
            edge_text = f"[Edge case answer for {q_num} by {stu['name']}] — This answer has a unique approach that doesn't clearly fit any main cluster."
            member = {
                "roll_number": stu["roll_number"],
                "name": stu["name"],
                "answer": {"q_number": q_num, "text": edge_text, "diagram_present": False, "diagram_description": None},
                "combined_text": f"[Text]: {edge_text}",
            }
            edge_cases.append({
                "cluster_id": f"{q_num}_edge_{ei}",
                "label": "Edge Case – Unique approach, needs manual review",
                "type": "edge_case",
                "student_count": 1,
                "students": [member],
                "representative": member,
                "matched_keywords": [],
                "keyword_match_pct": 0.0,
                "suggested_score": None,
                "graded": False,
                "score": None,
                "feedback": "",
            })

        exam_clusters[q_num] = {"clusters": clusters, "edge_cases": edge_cases}

    return {
        "exam_id": "demo_" + uuid4().hex[:8],
        "title": EXAM_TITLE,
        "exam_code": EXAM_CODE,
        "total_students": len(students),
        "questions": list(q_cluster_defs.keys()),
        "rubric": RUBRIC,
        "clusters": exam_clusters,
        "students": students,
        "status": "ready",
    }
